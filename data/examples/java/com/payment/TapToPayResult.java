package com.payment;

/**
 * Result of a tap-to-pay transaction.
 * Contains payment details, status, and any error information.
 */
public class TapToPayResult {

    private Payment payment;
    private boolean success;
    private boolean requiresReview;
    private String transactionId;
    private String authorizationCode;
    private String errorCode;
    private String message;

    private TapToPayResult() {}

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private final TapToPayResult result = new TapToPayResult();

        public Builder payment(Payment payment) {
            result.payment = payment;
            return this;
        }

        public Builder success(boolean success) {
            result.success = success;
            return this;
        }

        public Builder requiresReview(boolean requiresReview) {
            result.requiresReview = requiresReview;
            return this;
        }

        public Builder transactionId(String transactionId) {
            result.transactionId = transactionId;
            return this;
        }

        public Builder authorizationCode(String authorizationCode) {
            result.authorizationCode = authorizationCode;
            return this;
        }

        public Builder errorCode(String errorCode) {
            result.errorCode = errorCode;
            return this;
        }

        public Builder message(String message) {
            result.message = message;
            return this;
        }

        public TapToPayResult build() {
            return result;
        }
    }

    /**
     * Checks if the payment was approved.
     * @return true if approved
     */
    public boolean isApproved() {
        return success && payment != null && payment.getStatus() == PaymentStatus.COMPLETED;
    }

    /**
     * Checks if the payment was declined.
     * @return true if declined
     */
    public boolean isDeclined() {
        return !success && !requiresReview;
    }

    /**
     * Gets the appropriate status message for display.
     * @return status message
     */
    public String getStatusMessage() {
        if (isApproved()) {
            return "Payment Approved";
        }
        if (requiresReview) {
            return "Payment Under Review";
        }
        if (message != null) {
            return message;
        }
        return "Payment Failed";
    }

    // Getters
    public Payment getPayment() { return payment; }
    public boolean isSuccess() { return success; }
    public boolean isRequiresReview() { return requiresReview; }
    public String getTransactionId() { return transactionId; }
    public String getAuthorizationCode() { return authorizationCode; }
    public String getErrorCode() { return errorCode; }
    public String getMessage() { return message; }
}
