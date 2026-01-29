package com.payment;

import java.math.BigDecimal;

/**
 * Request object for tap-to-pay transactions on Android.
 * Contains card data read from NFC and transaction details.
 */
public class TapToPayRequest {

    private String terminalId;
    private String customerId;
    private BigDecimal amount;
    private String currency;
    private String description;
    private TapCardData cardData;
    private PaymentMetadata metadata;
    private String idempotencyKey;
    private boolean tipEnabled;
    private BigDecimal tipAmount;

    public TapToPayRequest() {
        this.currency = "USD";
        this.metadata = new PaymentMetadata();
    }

    /**
     * Builder for creating tap-to-pay requests.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private final TapToPayRequest request = new TapToPayRequest();

        public Builder terminalId(String terminalId) {
            request.terminalId = terminalId;
            return this;
        }

        public Builder customerId(String customerId) {
            request.customerId = customerId;
            return this;
        }

        public Builder amount(BigDecimal amount) {
            request.amount = amount;
            return this;
        }

        public Builder currency(String currency) {
            request.currency = currency;
            return this;
        }

        public Builder description(String description) {
            request.description = description;
            return this;
        }

        public Builder cardData(TapCardData cardData) {
            request.cardData = cardData;
            return this;
        }

        public Builder metadata(PaymentMetadata metadata) {
            request.metadata = metadata;
            return this;
        }

        public Builder idempotencyKey(String key) {
            request.idempotencyKey = key;
            return this;
        }

        public Builder withTip(BigDecimal tipAmount) {
            request.tipEnabled = true;
            request.tipAmount = tipAmount;
            return this;
        }

        public TapToPayRequest build() {
            return request;
        }
    }

    /**
     * Converts this request to a Payment entity.
     * @return Payment ready for processing
     */
    public Payment toPayment() {
        BigDecimal totalAmount = amount;
        if (tipEnabled && tipAmount != null) {
            totalAmount = amount.add(tipAmount);
        }

        Payment payment = new Payment(customerId, totalAmount, currency, PaymentMethod.TAP_TO_PAY);
        payment.setDescription(description);

        if (metadata == null) {
            metadata = new PaymentMetadata();
        }
        metadata.addAttribute("terminalId", terminalId);
        metadata.addAttribute("entryMode", "TAP");

        if (cardData != null) {
            metadata.addAttribute("cardBrand", cardData.getCardBrand());
            metadata.addAttribute("lastFour", cardData.getLastFourDigits());
        }

        if (tipEnabled && tipAmount != null) {
            metadata.addAttribute("tipAmount", tipAmount.toString());
            metadata.addAttribute("subtotal", amount.toString());
        }

        payment.setMetadata(metadata);
        return payment;
    }

    /**
     * Calculates the total amount including tip.
     * @return total amount
     */
    public BigDecimal getTotalAmount() {
        if (tipEnabled && tipAmount != null) {
            return amount.add(tipAmount);
        }
        return amount;
    }

    /**
     * Validates the tap-to-pay request.
     * @return true if valid
     */
    public boolean isValid() {
        if (terminalId == null || terminalId.isEmpty()) {
            return false;
        }
        if (amount == null || amount.compareTo(BigDecimal.ZERO) <= 0) {
            return false;
        }
        if (cardData == null || !cardData.isValid()) {
            return false;
        }
        return true;
    }

    // Getters
    public String getTerminalId() { return terminalId; }
    public String getCustomerId() { return customerId; }
    public BigDecimal getAmount() { return amount; }
    public String getCurrency() { return currency; }
    public String getDescription() { return description; }
    public TapCardData getCardData() { return cardData; }
    public PaymentMetadata getMetadata() { return metadata; }
    public String getIdempotencyKey() { return idempotencyKey; }
    public boolean isTipEnabled() { return tipEnabled; }
    public BigDecimal getTipAmount() { return tipAmount; }
}
