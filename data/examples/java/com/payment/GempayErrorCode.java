package com.payment;

/**
 * Chase Gempay specific error codes.
 * Maps to Chase API error responses for proper error handling.
 */
public enum GempayErrorCode {

    // Authentication errors
    INVALID_API_KEY("AUTH001", "Invalid API key", true),
    EXPIRED_API_KEY("AUTH002", "API key has expired", true),
    UNAUTHORIZED_MERCHANT("AUTH003", "Merchant not authorized", false),

    // Terminal/Device errors
    TERMINAL_NOT_REGISTERED("TERM001", "Terminal not registered", true),
    TERMINAL_INACTIVE("TERM002", "Terminal is inactive", true),
    INVALID_DEVICE_ID("TERM003", "Invalid device ID", false),
    DEVICE_ALREADY_REGISTERED("TERM004", "Device already registered", false),
    TERMINAL_SESSION_EXPIRED("TERM005", "Terminal session expired", true),

    // Transaction errors
    INVALID_AMOUNT("TXN001", "Invalid transaction amount", false),
    INVALID_CURRENCY("TXN002", "Invalid or unsupported currency", false),
    INVALID_TRANSACTION_ID("TXN003", "Invalid transaction ID", false),
    DUPLICATE_TRANSACTION("TXN004", "Duplicate transaction detected", false),
    TRANSACTION_NOT_FOUND("TXN005", "Transaction not found", false),
    TRANSACTION_ALREADY_VOIDED("TXN006", "Transaction already voided", false),
    TRANSACTION_ALREADY_REFUNDED("TXN007", "Transaction already refunded", false),

    // Card errors
    CARD_DECLINED("CARD001", "Card declined", false),
    INSUFFICIENT_FUNDS("CARD002", "Insufficient funds", false),
    CARD_EXPIRED("CARD003", "Card has expired", false),
    INVALID_CARD("CARD004", "Invalid card number", false),
    CARD_NOT_SUPPORTED("CARD005", "Card type not supported", false),
    CVV_MISMATCH("CARD006", "CVV verification failed", false),
    AVS_MISMATCH("CARD007", "Address verification failed", false),
    CARD_LOST_STOLEN("CARD008", "Card reported lost or stolen", false),

    // Tap-to-pay specific errors
    NFC_NOT_AVAILABLE("TAP001", "NFC not available on device", false),
    NFC_DISABLED("TAP002", "NFC is disabled", true),
    TAP_TIMEOUT("TAP003", "Tap timeout - card not detected", true),
    TAP_CANCELLED("TAP004", "Tap cancelled by user", false),
    TAP_READ_ERROR("TAP005", "Error reading card data", true),
    MULTIPLE_CARDS_DETECTED("TAP006", "Multiple cards detected", true),

    // Network/System errors
    NETWORK_ERROR("SYS001", "Network communication error", true),
    TIMEOUT("SYS002", "Request timeout", true),
    SERVICE_UNAVAILABLE("SYS003", "Service temporarily unavailable", true),
    INTERNAL_ERROR("SYS004", "Internal server error", true),
    RATE_LIMITED("SYS005", "Rate limit exceeded", true),

    // Unknown
    UNKNOWN("UNK001", "Unknown error", false);

    private final String code;
    private final String message;
    private final boolean retryable;

    GempayErrorCode(String code, String message, boolean retryable) {
        this.code = code;
        this.message = message;
        this.retryable = retryable;
    }

    public String getCode() {
        return code;
    }

    public String getMessage() {
        return message;
    }

    public boolean isRetryable() {
        return retryable;
    }

    /**
     * Finds an error code by its string code.
     * @param code the error code string
     * @return the matching enum, or UNKNOWN if not found
     */
    public static GempayErrorCode fromCode(String code) {
        for (GempayErrorCode errorCode : values()) {
            if (errorCode.code.equals(code)) {
                return errorCode;
            }
        }
        return UNKNOWN;
    }

    /**
     * Checks if this is a card-related error.
     * @return true if card error
     */
    public boolean isCardError() {
        return code.startsWith("CARD");
    }

    /**
     * Checks if this is a terminal/device error.
     * @return true if terminal error
     */
    public boolean isTerminalError() {
        return code.startsWith("TERM");
    }

    /**
     * Checks if this is a tap-to-pay error.
     * @return true if tap error
     */
    public boolean isTapError() {
        return code.startsWith("TAP");
    }

    /**
     * Gets a user-friendly error message.
     * @return message suitable for displaying to end user
     */
    public String getUserFriendlyMessage() {
        switch (this) {
            case CARD_DECLINED:
                return "Your card was declined. Please try a different card.";
            case INSUFFICIENT_FUNDS:
                return "Insufficient funds. Please try a different card.";
            case CARD_EXPIRED:
                return "Your card has expired. Please use a valid card.";
            case TAP_TIMEOUT:
                return "Card not detected. Please tap your card again.";
            case TAP_CANCELLED:
                return "Payment cancelled.";
            case MULTIPLE_CARDS_DETECTED:
                return "Multiple cards detected. Please tap one card at a time.";
            case NFC_DISABLED:
                return "Please enable NFC in your device settings.";
            case NETWORK_ERROR:
            case TIMEOUT:
            case SERVICE_UNAVAILABLE:
                return "Connection error. Please try again.";
            default:
                return "Payment failed. Please try again.";
        }
    }
}
