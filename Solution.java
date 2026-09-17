class Solution {
    public int longestOnes(int[] nums, int k) {
        int left = 0; // Start of the sliding window
        int right; // End of the sliding window
        int maxOnes = 0; // Maximum length of window found
        int zerosCount = 0; // Current count of zeros in the window

        // Expand the window with 'right' pointer
        for (right = 0; right < nums.length; right++) {
            if (nums[right] == 0) {
                zerosCount++; // Include zero and increment count
            }

            // If we have more than 'k' zeros, shrink from the left
            while (zerosCount > k) {
                if (nums[left] == 0) {
                    zerosCount--; // Zero leaves the window
                }
                left++; // Shrink window
            }

            // Update the maximum length found so far
            maxOnes = Math.max(maxOnes, right - left + 1);
        }

        return maxOnes;
    }
}