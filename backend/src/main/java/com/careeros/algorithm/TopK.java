package com.careeros.algorithm;

/**
 * Top-K selection utilities.
 * Finds the top K elements from a collection based on a score function.
 */
public class TopK {

  /** Return the indices of the top K elements in descending order of score. */
  public static <T> int[] select(T[] items, int K, ScoreFn<T> fn) {
    if (K <= 0 || items == null || items.length == 0) {
      return new int[0];
    }
    K = Math.min(K, items.length);
    // The scan walks every element first (the abandoned version allocated only K
    // slots and walked the full length straight into an IndexOutOfBounds), then the
    // insertion pass keeps just the best K at the front.
    int[] indices = new int[items.length];
    for (int i = 0; i < items.length; i++) {
      indices[i] = i;
    }
    // Simple selection: sort by score descending
    // Use insertion sort for small arrays
    for (int i = 1; i < indices.length; i++) {
      int keyIdx = indices[i];
      T keyItem = items[keyIdx];
      int j = i - 1;
      while (j >= 0 && fn.score(items[indices[j]]) < fn.score(keyItem)) {
        indices[j + 1] = indices[j];
        j--;
      }
      indices[j + 1] = keyIdx;
    }
    // Return only the top K
    return java.util.Arrays.copyOf(indices, K);
  }

  /** Functional interface for scoring items. */
  @FunctionalInterface
  public interface ScoreFn<T> {
    double score(T item);
  }
}