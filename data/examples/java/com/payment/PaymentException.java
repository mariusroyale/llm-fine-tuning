package com.payment;

/**
 * Exception thrown when payment processing fails.
 * Contains an error code for programmatic handling.
 */
public class PaymentException extends Exception {

    private final String errorCode;

    public PaymentException(String message, String errorCode) {
        super(message);
        this.errorCode = errorCode;
    }

    public PaymentException(String message, String errorCode, Throwable cause) {
        super(message, cause);
        this.errorCode = errorCode;
    }

    public String getErrorCode() {
        return errorCode;
    }

    /**
     * Checks if this is a retryable error.
     * @return true if the operation can be retried
     */
    public boolean isRetryable() {
        return "GATEWAY_ERROR".equals(errorCode) ||
               "TIMEOUT".equals(errorCode) ||
               "NETWORK_ERROR".equals(errorCode);
    }

    /**
     * Checks if this is a validation error.
     * @return true if caused by invalid input
     */
    public boolean isValidationError() {
        return "VALIDATION_ERROR".equals(errorCode) ||
               "INVALID_AMOUNT".equals(errorCode) ||
               "INVALID_STATUS".equals(errorCode);
    }
}
