package com.payment;

import java.math.BigDecimal;

/**
 * Internal request object for Chase Gempay API charge calls.
 * Maps payment data to Gempay API format.
 */
public class GempayChargeRequest {

    private BigDecimal amount;
    private String currency;
    private String merchantId;
    private String terminalId;
    private String description;
    private String encryptedCardData;
    private String entryMode;
    private String transactionType;

    public GempayChargeRequest(BigDecimal amount, String currency, String merchantId,
                                String terminalId, String description) {
        this.amount = amount;
        this.currency = currency;
        this.merchantId = merchantId;
        this.terminalId = terminalId;
        this.description = description;
        this.transactionType = "SALE";
    }

    /**
     * Converts to JSON string for API call.
     * @return JSON representation
     */
    public String toJson() {
        StringBuilder json = new StringBuilder();
        json.append("{");
        json.append("\"amount\":").append(getAmountInCents()).append(",");
        json.append("\"currency\":\"").append(currency).append("\",");
        json.append("\"merchantId\":\"").append(merchantId).append("\",");

        if (terminalId != null) {
            json.append("\"terminalId\":\"").append(terminalId).append("\",");
        }
        if (description != null) {
            json.append("\"description\":\"").append(escapeJson(description)).append("\",");
        }
        if (encryptedCardData != null) {
            json.append("\"encryptedCardData\":\"").append(encryptedCardData).append("\",");
        }
        if (entryMode != null) {
            json.append("\"entryMode\":\"").append(entryMode).append("\",");
        }

        json.append("\"transactionType\":\"").append(transactionType).append("\"");
        json.append("}");

        return json.toString();
    }

    /**
     * Gets the amount in cents (for API call).
     * @return amount in smallest currency unit
     */
    public int getAmountInCents() {
        return amount.multiply(new BigDecimal("100")).intValue();
    }

    private String escapeJson(String value) {
        if (value == null) return "";
        return value.replace("\\", "\\\\")
                    .replace("\"", "\\\"")
                    .replace("\n", "\\n")
                    .replace("\r", "\\r");
    }

    // Getters and setters
    public BigDecimal getAmount() { return amount; }
    public void setAmount(BigDecimal amount) { this.amount = amount; }

    public String getCurrency() { return currency; }
    public void setCurrency(String currency) { this.currency = currency; }

    public String getMerchantId() { return merchantId; }
    public void setMerchantId(String merchantId) { this.merchantId = merchantId; }

    public String getTerminalId() { return terminalId; }
    public void setTerminalId(String terminalId) { this.terminalId = terminalId; }

    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }

    public String getEncryptedCardData() { return encryptedCardData; }
    public void setEncryptedCardData(String encryptedCardData) {
        this.encryptedCardData = encryptedCardData;
    }

    public String getEntryMode() { return entryMode; }
    public void setEntryMode(String entryMode) { this.entryMode = entryMode; }

    public String getTransactionType() { return transactionType; }
    public void setTransactionType(String transactionType) {
        this.transactionType = transactionType;
    }
}
