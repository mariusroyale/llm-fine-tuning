package com.payment;

/**
 * Supported payment methods in the system.
 * Includes tap-to-pay methods for Chase Gempay Android integration.
 */
public enum PaymentMethod {

    CREDIT_CARD("Credit Card", true, 2.9, false),
    DEBIT_CARD("Debit Card", true, 1.5, false),
    TAP_TO_PAY("Tap to Pay", true, 2.6, true),
    TAP_TO_PAY_CREDIT("Tap to Pay - Credit", true, 2.9, true),
    TAP_TO_PAY_DEBIT("Tap to Pay - Debit", true, 1.5, true),
    CONTACTLESS_NFC("Contactless NFC", true, 2.6, true),
    MANUAL_ENTRY("Manual Card Entry", true, 3.2, false),
    BANK_TRANSFER("Bank Transfer", false, 0.5, false),
    APPLE_PAY("Apple Pay", true, 2.9, true),
    GOOGLE_PAY("Google Pay", true, 2.9, true),
    SAMSUNG_PAY("Samsung Pay", true, 2.9, true);

    private final String displayName;
    private final boolean supportsInstantPayment;
    private final double feePercentage;
    private final boolean isContactless;

    PaymentMethod(String displayName, boolean supportsInstantPayment, double feePercentage, boolean isContactless) {
        this.displayName = displayName;
        this.supportsInstantPayment = supportsInstantPayment;
        this.feePercentage = feePercentage;
        this.isContactless = isContactless;
    }

    public String getDisplayName() {
        return displayName;
    }

    public boolean supportsInstantPayment() {
        return supportsInstantPayment;
    }

    public double getFeePercentage() {
        return feePercentage;
    }

    public boolean isContactless() {
        return isContactless;
    }

    /**
     * Checks if this is a tap-to-pay method.
     * @return true if tap-to-pay
     */
    public boolean isTapToPay() {
        return this == TAP_TO_PAY || this == TAP_TO_PAY_CREDIT ||
               this == TAP_TO_PAY_DEBIT || this == CONTACTLESS_NFC;
    }

    /**
     * Checks if this payment method requires a physical terminal/device.
     * @return true if terminal required
     */
    public boolean requiresTerminal() {
        return isContactless || this == MANUAL_ENTRY;
    }

    /**
     * Checks if this payment method requires additional verification.
     * @return true if verification is required
     */
    public boolean requiresVerification() {
        return this == BANK_TRANSFER || this == MANUAL_ENTRY;
    }
}
