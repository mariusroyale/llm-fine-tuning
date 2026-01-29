package com.payment;

/**
 * Credit/debit card details for payment processing.
 * Note: In production, never store raw card numbers - use tokenization.
 */
public class CardDetails {

    private String cardToken;
    private String lastFourDigits;
    private String cardBrand;
    private String expiryMonth;
    private String expiryYear;
    private String cardholderName;
    private String billingZip;

    public CardDetails() {}

    /**
     * Creates card details from a tokenized card.
     * @param cardToken the payment provider token
     * @param lastFourDigits last 4 digits for display
     * @param cardBrand the card brand (VISA, MASTERCARD, etc.)
     */
    public CardDetails(String cardToken, String lastFourDigits, String cardBrand) {
        this.cardToken = cardToken;
        this.lastFourDigits = lastFourDigits;
        this.cardBrand = cardBrand;
    }

    /**
     * Returns a masked display string for the card.
     * @return masked card number like "**** **** **** 1234"
     */
    public String getMaskedNumber() {
        return "**** **** **** " + (lastFourDigits != null ? lastFourDigits : "****");
    }

    /**
     * Checks if the card is expired.
     * @param currentMonth current month (1-12)
     * @param currentYear current year (4 digits)
     * @return true if expired
     */
    public boolean isExpired(int currentMonth, int currentYear) {
        if (expiryYear == null || expiryMonth == null) {
            return true;
        }
        int expYear = Integer.parseInt(expiryYear);
        int expMonth = Integer.parseInt(expiryMonth);

        if (expYear < currentYear) {
            return true;
        }
        if (expYear == currentYear && expMonth < currentMonth) {
            return true;
        }
        return false;
    }

    // Getters and setters
    public String getCardToken() { return cardToken; }
    public void setCardToken(String cardToken) { this.cardToken = cardToken; }

    public String getLastFourDigits() { return lastFourDigits; }
    public void setLastFourDigits(String lastFourDigits) { this.lastFourDigits = lastFourDigits; }

    public String getCardBrand() { return cardBrand; }
    public void setCardBrand(String cardBrand) { this.cardBrand = cardBrand; }

    public String getExpiryMonth() { return expiryMonth; }
    public void setExpiryMonth(String expiryMonth) { this.expiryMonth = expiryMonth; }

    public String getExpiryYear() { return expiryYear; }
    public void setExpiryYear(String expiryYear) { this.expiryYear = expiryYear; }

    public String getCardholderName() { return cardholderName; }
    public void setCardholderName(String cardholderName) { this.cardholderName = cardholderName; }

    public String getBillingZip() { return billingZip; }
    public void setBillingZip(String billingZip) { this.billingZip = billingZip; }
}
