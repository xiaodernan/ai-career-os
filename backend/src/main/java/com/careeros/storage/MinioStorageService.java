package com.careeros.storage;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.config.AppProperties;
import io.minio.BucketExistsArgs;
import io.minio.GetObjectArgs;
import io.minio.GetPresignedObjectUrlArgs;
import io.minio.ListObjectsArgs;
import io.minio.MakeBucketArgs;
import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import io.minio.RemoveObjectArgs;
import io.minio.Result;
import io.minio.http.Method;
import io.minio.messages.Item;
import jakarta.annotation.PostConstruct;
import java.io.ByteArrayInputStream;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.ZonedDateTime;
import java.util.ArrayList;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

@Service
@ConditionalOnProperty(prefix = "app.storage", name = "enabled", havingValue = "true", matchIfMissing = true)
public class MinioStorageService implements StorageService {

    private static final Logger log = LoggerFactory.getLogger(MinioStorageService.class);

    private final MinioClient client;
    private final String bucket;

    public MinioStorageService(AppProperties props) {
        AppProperties.Storage storage = props.getStorage();
        this.bucket = storage.getBucket();
        this.client = MinioClient.builder()
                .endpoint(storage.getEndpoint())
                .credentials(storage.getAccessKey(), storage.getSecretKey())
                .build();
    }

    /** Guard: the private bucket must exist before the first upload. */
    @PostConstruct
    void ensureBucketExists() {
        try {
            boolean exists = client.bucketExists(BucketExistsArgs.builder().bucket(bucket).build());
            if (!exists) {
                client.makeBucket(MakeBucketArgs.builder().bucket(bucket).build());
                log.info("Created MinIO bucket {}", bucket);
            }
        } catch (Exception e) {
            throw new IllegalStateException("Cannot reach object storage (MinIO) at startup", e);
        }
    }

    @Override
    public void put(String key, byte[] content, String contentType) {
        try {
            client.putObject(PutObjectArgs.builder()
                    .bucket(bucket)
                    .object(key)
                    .stream(new ByteArrayInputStream(content), content.length, -1)
                    .contentType(contentType)
                    .build());
        } catch (Exception e) {
            throw new ApiException(ApiErrorCode.STORAGE_WRITE_FAILED, "Object storage write failed");
        }
    }

    @Override
    public String getPresignedUrl(String key, Duration ttl) {
        try {
            return client.getPresignedObjectUrl(GetPresignedObjectUrlArgs.builder()
                    .method(Method.GET)
                    .bucket(bucket)
                    .object(key)
                    .expiry((int) ttl.toSeconds())
                    .build());
        } catch (Exception e) {
            throw new ApiException(ApiErrorCode.STORAGE_PRESIGN_FAILED, "Object storage presign failed");
        }
    }

    @Override
    public void delete(String key) {
        try {
            client.removeObject(RemoveObjectArgs.builder().bucket(bucket).object(key).build());
        } catch (Exception e) {
            throw new ApiException(ApiErrorCode.STORAGE_DELETE_FAILED, "Object storage delete failed");
        }
    }

    @Override
    public byte[] getBytes(String key) {
        try (var stream = client.getObject(GetObjectArgs.builder().bucket(bucket).object(key).build())) {
            return stream.readAllBytes();
        } catch (Exception e) {
            throw new ApiException(ApiErrorCode.STORAGE_READ_FAILED, "Object storage read failed");
        }
    }

    /**
     * Every object is accumulated before anything is returned, because the port's promise is that a
     * listing either covers the bucket or throws: a method that returned what it had reached when the
     * store went quiet would hand a sweep a short list and let it delete what that list never showed.
     * The walk therefore sits inside the same try as the call that starts it, so a refusal anywhere --
     * on the first page or the tenth -- is a refusal of the whole listing. Pagination is the client's
     * own, and its errors surface as a failed item, which is why reading each item is inside the try.
     */
    @Override
    public List<StoredObject> list() {
        try {
            List<StoredObject> objects = new ArrayList<>();
            for (Result<Item> result : client.listObjects(ListObjectsArgs.builder()
                    .bucket(bucket)
                    .recursive(true)
                    .build())) {
                Item item = result.get();
                ZonedDateTime stamp = item.lastModified();
                objects.add(new StoredObject(item.objectName(),
                        stamp == null ? OffsetDateTime.now() : stamp.toOffsetDateTime(),
                        item.size()));
            }
            return objects;
        } catch (Exception e) {
            // One code answers with one sentence: the reader's message is chosen from the code, so a
            // listing-specific wording would make STORAGE_READ_FAILED mean two things at once. Which
            // read failed is in the cause this throw carries.
            throw new ApiException(ApiErrorCode.STORAGE_READ_FAILED, "Object storage read failed");
        }
    }

    /**
     * One bucket-existence round trip is the cheapest question MinIO answers, and it is the
     * same one boot asks: if the bucket is gone, every upload is about to fail. A false here
     * is a report, not an error -- the health line is where it belongs.
     */
    @Override
    public boolean available() {
        try {
            return client.bucketExists(BucketExistsArgs.builder().bucket(bucket).build());
        } catch (Exception e) {
            return false;
        }
    }
}
