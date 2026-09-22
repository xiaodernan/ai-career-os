package com.careeros.resume.service;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class SkillNormalizerTest {

    @Test
    void nullAndBlankBecomeEmpty() {
        assertEquals("", SkillNormalizer.normalize(null));
    }

    @Test
    void lowercasesTrimsAndCollapsesSpaces() {
        assertEquals("python", SkillNormalizer.normalize("  Python  "));
        assertEquals("machine learning", SkillNormalizer.normalize("Machine   Learning"));
    }

    @Test
    void resolvesDirectAliases() {
        assertEquals("javascript", SkillNormalizer.normalize("JS"));
        assertEquals("kubernetes", SkillNormalizer.normalize("k8s"));
        assertEquals("go", SkillNormalizer.normalize("Golang"));
        assertEquals("postgresql", SkillNormalizer.normalize("Postgres"));
        assertEquals("react", SkillNormalizer.normalize("ReactJS"));
        assertEquals("tensorflow", SkillNormalizer.normalize("TF"));
    }

    @Test
    void separatorVariantsCollapseOntoTheSameCanonical() {
        // The (user_id, name_norm) unique key must not fragment one skill into rows.
        assertEquals("react", SkillNormalizer.normalize("React JS"));
        assertEquals("react", SkillNormalizer.normalize("react-js"));
        assertEquals("react", SkillNormalizer.normalize("React.js"));
        assertEquals("node.js", SkillNormalizer.normalize("Node JS"));
        assertEquals("node.js", SkillNormalizer.normalize("nodejs"));
        assertEquals("node.js", SkillNormalizer.normalize("Node.js"));
        assertEquals("next.js", SkillNormalizer.normalize("Next JS"));
    }

    @Test
    void keepsPunctuatedSkillNamesIntact() {
        assertEquals("c++", SkillNormalizer.normalize("C++"));
        assertEquals("c#", SkillNormalizer.normalize("C#"));
    }

    @Test
    void leavesUnaliasedSkillsUnchanged() {
        assertEquals("rust", SkillNormalizer.normalize("Rust"));
        assertEquals("go", SkillNormalizer.normalize("Go"));
    }
}
