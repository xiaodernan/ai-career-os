package com.careeros.common;

import java.util.List;
import java.util.Map;

/** Null/type-safe readers for loosely-typed JSON payloads (ai-service responses, jsonb columns). */
public final class Json {

    private Json() {
    }

    @SuppressWarnings("unchecked")
    public static Map<String, Object> obj(Object v) {
        return v instanceof Map ? (Map<String, Object>) v : Map.of();
    }

    @SuppressWarnings("unchecked")
    public static List<Object> arr(Object v) {
        return v instanceof List ? (List<Object>) v : List.of();
    }

    @SuppressWarnings("unchecked")
    public static List<String> strList(Object v) {
        if (!(v instanceof List<?> list)) {
            return List.of();
        }
        return list.stream().filter(o -> o != null).map(String::valueOf).toList();
    }

    public static String str(Map<String, Object> m, String key) {
        Object v = m.get(key);
        return v == null ? null : String.valueOf(v);
    }

    public static String strOr(Map<String, Object> m, String key, String fallback) {
        String s = str(m, key);
        return s == null || s.isBlank() ? fallback : s;
    }

    public static Double dbl(Map<String, Object> m, String key) {
        Object v = m.get(key);
        if (v instanceof Number n) {
            return n.doubleValue();
        }
        if (v instanceof String s) {
            try {
                return Double.parseDouble(s);
            } catch (NumberFormatException e) {
                return null;
            }
        }
        return null;
    }

    public static float flt(Map<String, Object> m, String key, float fallback) {
        Double d = dbl(m, key);
        return d == null ? fallback : d.floatValue();
    }

    public static Integer integer(Map<String, Object> m, String key) {
        Double d = dbl(m, key);
        return d == null ? null : (int) Math.round(d);
    }

    public static java.util.UUID uuidOrNull(Map<String, Object> m, String key) {
        String s = str(m, key);
        if (s == null || s.isBlank()) {
            return null;
        }
        try {
            return java.util.UUID.fromString(s);
        } catch (IllegalArgumentException e) {
            return null;
        }
    }
}
