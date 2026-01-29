package com.payment;

/**
 * Represents the possible states of a payment transaction.
 */
public enum PaymentStatus {

    /** Payment has been created but not yet processed */
    PENDING,

    /** Payment is currently being processed by the provider */
    PROCESSING,

    /** Payment has been successfully completed */
    COMPLETED,

    /** Payment has failed */
    FAILED,

    /** Payment was cancelled by the user or system */
    CANCELLED,

    /** Payment has been refunded */
    REFUNDED,

    /** Payment is under review for fraud */
    UNDER_REVIEW;

    /**
     * Checks if the payment is in a terminal state (cannot change).
     * @return true if the status is terminal
     */
    public boolean isTerminal() {
        return this == COMPLETED || this == FAILED || this == CANCELLED || this == REFUNDED;
    }

    /**
     * Checks if the payment can be refunded.
     * @return true if refund is possible
     */
    public boolean canRefund() {
        return this == COMPLETED;
    }

    /**
     * Checks if the payment can be cancelled.
     * @return true if cancellation is possible
     */
    public boolean canCancel() {
        return this == PENDING || this == UNDER_REVIEW;
    }
}
