package com.payment;

import java.math.BigDecimal;

/**
 * Result of a refund operation.
 */
public class RefundResult {

    private final boolean successful;
    private final String refundTransactionId;
    private final BigDecimal refundedAmount;
    private final String errorMessage;

    public RefundResult(boolean successful, String refundTransactionId, BigDecimal refundedAmount) {
        this(successful, refundTransactionId, refundedAmount, null);
    }

    public RefundResult(boolean successful, String refundTransactionId, BigDecimal refundedAmount, String errorMessage) {
        this.successful = successful;
        this.refundTransactionId = refundTransactionId;
        this.refundedAmount = refundedAmount;
        this.errorMessage = errorMessage;
    }

    public boolean isSuccessful() { return successful; }
    public String getRefundTransactionId() { return refundTransactionId; }
    public BigDecimal getRefundedAmount() { return refundedAmount; }
    public String getErrorMessage() { return errorMessage; }
}
