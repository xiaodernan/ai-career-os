# syntax=docker/dockerfile:1
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /m
COPY pom.xml .
# The dev network corrupts long downloads on occasion (truncated artifact bodies);
# a retry handler count of 5 recovers transiently dropped bytes instead of failing the build.
RUN mvn -B -q -Dmaven.wagon.http.retryHandler.count=5 dependency:go-offline
COPY src ./src
RUN mvn -B -q -DskipTests -Dmaven.wagon.http.retryHandler.count=5 package

FROM eclipse-temurin:21-jre-alpine
RUN addgroup -S app && adduser -S app -G app
WORKDIR /opt
COPY --from=build /m/target/*.jar app.jar
# Epic 78: bake the commit this image is built from, so /health can name it.
ARG APP_BUILD_SHA=dev
ENV APP_BUILD_SHA=${APP_BUILD_SHA}
USER app
EXPOSE 8080
ENTRYPOINT ["java","-XX:MaxRAMPercentage=75","-jar","/opt/app.jar"]
