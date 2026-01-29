package com.payment;

import java.math.BigDecimal;

/**
 * Request object for creating a new payment.
 * Contains all information needed to initiate a payment transaction.
 */
public class PaymentRequest {

    private String customerId;
    private BigDecimal amount;
    private String currency;
    private PaymentMethod method;
    private String description;
    private PaymentMetadata metadata;
    private String idempotencyKey;
    private CardDetails cardDetails;
    private BankDetails bankDetails;

    public PaymentRequest() {}

    public PaymentRequest(String customerId, BigDecimal amount, String currency, PaymentMethod method) {
        this.customerId = customerId;
        this.amount = amount;
        this.currency = currency;
        this.method = method;
    }

    /**
     * Builder pattern for creating payment requests.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private final PaymentRequest request = new PaymentRequest();

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

        public Builder method(PaymentMethod method) {
            request.method = method;
            return this;
        }

        public Builder description(String description) {
            request.description = description;
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

        public Builder cardDetails(CardDetails cardDetails) {
            request.cardDetails = cardDetails;
            return this;
        }

        public Builder bankDetails(BankDetails bankDetails) {
            request.bankDetails = bankDetails;
            return this;
        }

        public PaymentRequest build() {
            return request;
        }
    }

    // Getters
    public String getCustomerId() { return customerId; }
    public BigDecimal getAmount() { return amount; }
    public String getCurrency() { return currency; }
    public PaymentMethod getMethod() { return method; }
    public String getDescription() { return description; }
    public PaymentMetadata getMetadata() { return metadata; }
    public String getIdempotencyKey() { return idempotencyKey; }
    public CardDetails getCardDetails() { return cardDetails; }
    public BankDetails getBankDetails() { return bankDetails; }
}
