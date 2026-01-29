package com.payment;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.UUID;

/**
 * Represents a payment transaction in the system.
 * Contains all details about a single payment including amount,
 * currency, status, and associated metadata.
 */
public class Payment {

    private UUID id;
    private String customerId;
    private BigDecimal amount;
    private String currency;
    private PaymentStatus status;
    private PaymentMethod method;
    private String description;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private String externalReference;
    private PaymentMetadata metadata;

    public Payment() {
        this.id = UUID.randomUUID();
        this.status = PaymentStatus.PENDING;
        this.createdAt = LocalDateTime.now();
        this.updatedAt = LocalDateTime.now();
    }

    public Payment(String customerId, BigDecimal amount, String currency, PaymentMethod method) {
        this();
        this.customerId = customerId;
        this.amount = amount;
        this.currency = currency;
        this.method = method;
    }

    /**
     * Validates that the payment has all required fields and valid values.
     * @return true if the payment is valid, false otherwise
     */
    public boolean isValid() {
        if (customerId == null || customerId.isEmpty()) {
            return false;
        }
        if (amount == null || amount.compareTo(BigDecimal.ZERO) <= 0) {
            return false;
        }
        if (currency == null || currency.length() != 3) {
            return false;
        }
        if (method == null) {
            return false;
        }
        return true;
    }

    /**
     * Marks the payment as completed with an external reference.
     * @param externalReference the reference from the payment provider
     */
    public void markCompleted(String externalReference) {
        this.status = PaymentStatus.COMPLETED;
        this.externalReference = externalReference;
        this.updatedAt = LocalDateTime.now();
    }

    /**
     * Marks the payment as failed with a reason.
     * @param reason the failure reason
     */
    public void markFailed(String reason) {
        this.status = PaymentStatus.FAILED;
        if (this.metadata == null) {
            this.metadata = new PaymentMetadata();
        }
        this.metadata.setFailureReason(reason);
        this.updatedAt = LocalDateTime.now();
    }

    // Getters and setters
    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public String getCustomerId() { return customerId; }
    public void setCustomerId(String customerId) { this.customerId = customerId; }

    public BigDecimal getAmount() { return amount; }
    public void setAmount(BigDecimal amount) { this.amount = amount; }

    public String getCurrency() { return currency; }
    public void setCurrency(String currency) { this.currency = currency; }

    public PaymentStatus getStatus() { return status; }
    public void setStatus(PaymentStatus status) { this.status = status; }

    public PaymentMethod getMethod() { return method; }
    public void setMethod(PaymentMethod method) { this.method = method; }

    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }

    public String getExternalReference() { return externalReference; }
    public PaymentMetadata getMetadata() { return metadata; }
    public void setMetadata(PaymentMetadata metadata) { this.metadata = metadata; }
}
