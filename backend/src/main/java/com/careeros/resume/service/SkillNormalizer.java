package com.careeros.resume.service;

import java.text.Normalizer;
import java.util.Map;
import java.util.regex.Pattern;

/** Lightweight skill-name canonicalization; the DB unique key is (user_id, name_norm). */
public final class SkillNormalizer {

    private static final Pattern NON_ALNUM = Pattern.compile("[^a-z0-9+#. ]+");
    private static final Pattern SPACES = Pattern.compile("\\s+");

    private static final Map<String, String> ALIASES = Map.ofEntries(
            Map.entry("js", "javascript"),
            Map.entry("ts", "typescript"),
            Map.entry("k8s", "kubernetes"),
            Map.entry("golang", "go"),
            Map.entry("postgres", "postgresql"),
            Map.entry("reactjs", "react"),
            Map.entry("nextjs", "next.js"),
            Map.entry("nodejs", "node.js"),
            Map.entry("pytorch", "pytorch"),
            Map.entry("tf", "tensorflow"));

    private SkillNormalizer() {
    }

    /** Separator-free form used only for alias lookup (react.js / react js → reactjs). */
    private static String tighten(String s) {
        return s.replaceAll("[ .\\-]+", "");
    }

    public static String normalize(String name) {
        if (name == null) {
            return "";
        }
        String s = Normalizer.normalize(name, Normalizer.Form.NFKC).toLowerCase().trim();
        s = NON_ALNUM.matcher(s).replaceAll(" ");
        s = SPACES.matcher(s).replaceAll(" ").trim();
        String alias = ALIASES.get(s);
        if (alias == null) {
            // Collapse separator variants ("React JS", "react-js") onto the same alias so
            // the (user_id, name_norm) unique key can't store duplicate skills.
            alias = ALIASES.get(tighten(s));
        }
        return alias != null ? alias : s;
    }
}
