package com.payment;

/**
 * Card data captured from NFC tap-to-pay.
 * Contains encrypted card information for secure transmission.
 */
public class TapCardData {

    private String encryptedTrackData;
    private String lastFourDigits;
    private String cardBrand;
    private String expiryMonth;
    private String expiryYear;
    private String cardholderName;
    private String applicationLabel;
    private String applicationIdentifier;
    private String cryptogram;
    private String cryptogramType;
    private String panSequenceNumber;
    private boolean pinVerified;

    public TapCardData() {}

    /**
     * Creates card data from NFC read result.
     * @param encryptedTrackData encrypted track data from NFC
     * @param lastFourDigits last 4 digits for display
     * @param cardBrand detected card brand
     */
    public TapCardData(String encryptedTrackData, String lastFourDigits, String cardBrand) {
        this.encryptedTrackData = encryptedTrackData;
        this.lastFourDigits = lastFourDigits;
        this.cardBrand = cardBrand;
    }

    /**
     * Validates that required card data is present.
     * @return true if valid
     */
    public boolean isValid() {
        return encryptedTrackData != null && !encryptedTrackData.isEmpty() &&
               lastFourDigits != null && lastFourDigits.length() == 4 &&
               cardBrand != null;
    }

    /**
     * Gets the masked card number for display.
     * @return masked number like "**** **** **** 1234"
     */
    public String getMaskedNumber() {
        return "**** **** **** " + (lastFourDigits != null ? lastFourDigits : "****");
    }

    /**
     * Gets the card brand display name.
     * @return brand name like "Visa" or "Mastercard"
     */
    public String getCardBrandDisplayName() {
        if (cardBrand == null) {
            return "Card";
        }
        switch (cardBrand.toUpperCase()) {
            case "VISA":
                return "Visa";
            case "MASTERCARD":
            case "MC":
                return "Mastercard";
            case "AMEX":
            case "AMERICAN EXPRESS":
                return "American Express";
            case "DISCOVER":
                return "Discover";
            default:
                return cardBrand;
        }
    }

    /**
     * Checks if this is a debit card based on application identifier.
     * @return true if debit card
     */
    public boolean isDebitCard() {
        if (applicationIdentifier == null) {
            return false;
        }
        // Common debit AIDs
        return applicationIdentifier.startsWith("A000000098") || // Visa Debit
               applicationIdentifier.contains("DEBIT");
    }

    // Getters and setters
    public String getEncryptedTrackData() { return encryptedTrackData; }
    public void setEncryptedTrackData(String encryptedTrackData) {
        this.encryptedTrackData = encryptedTrackData;
    }

    public String getLastFourDigits() { return lastFourDigits; }
    public void setLastFourDigits(String lastFourDigits) {
        this.lastFourDigits = lastFourDigits;
    }

    public String getCardBrand() { return cardBrand; }
    public void setCardBrand(String cardBrand) { this.cardBrand = cardBrand; }

    public String getExpiryMonth() { return expiryMonth; }
    public void setExpiryMonth(String expiryMonth) { this.expiryMonth = expiryMonth; }

    public String getExpiryYear() { return expiryYear; }
    public void setExpiryYear(String expiryYear) { this.expiryYear = expiryYear; }

    public String getCardholderName() { return cardholderName; }
    public void setCardholderName(String cardholderName) { this.cardholderName = cardholderName; }

    public String getApplicationLabel() { return applicationLabel; }
    public void setApplicationLabel(String applicationLabel) {
        this.applicationLabel = applicationLabel;
    }

    public String getApplicationIdentifier() { return applicationIdentifier; }
    public void setApplicationIdentifier(String applicationIdentifier) {
        this.applicationIdentifier = applicationIdentifier;
    }

    public String getCryptogram() { return cryptogram; }
    public void setCryptogram(String cryptogram) { this.cryptogram = cryptogram; }

    public String getCryptogramType() { return cryptogramType; }
    public void setCryptogramType(String cryptogramType) { this.cryptogramType = cryptogramType; }

    public String getPanSequenceNumber() { return panSequenceNumber; }
    public void setPanSequenceNumber(String panSequenceNumber) {
        this.panSequenceNumber = panSequenceNumber;
    }

    public boolean isPinVerified() { return pinVerified; }
    public void setPinVerified(boolean pinVerified) { this.pinVerified = pinVerified; }
}
