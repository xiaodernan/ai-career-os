package com.careeros.resume.entity;

import java.io.Serializable;
import java.util.UUID;

public record ResumeSkillId(UUID resumeVersionId, UUID skillId) implements Serializable {
}
