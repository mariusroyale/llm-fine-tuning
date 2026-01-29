package com.payment;

import java.math.BigDecimal;

/**
 * Service for sending payment-related notifications.
 * Handles email, SMS, and webhook notifications.
 */
public interface NotificationService {

    /**
     * Notifies about a successful payment.
     * @param payment the completed payment
     */
    void notifyPaymentSuccess(Payment payment);

    /**
     * Notifies about a failed payment.
     * @param payment the failed payment
     */
    void notifyPaymentFailure(Payment payment);

    /**
     * Notifies about a cancelled payment.
     * @param payment the cancelled payment
     */
    void notifyPaymentCancelled(Payment payment);

    /**
     * Notifies about a successful refund.
     * @param payment the refunded payment
     * @param amount the refund amount
     */
    void notifyRefundSuccess(Payment payment, BigDecimal amount);

    /**
     * Notifies fraud team about a payment under review.
     * @param payment the suspicious payment
     */
    void notifyFraudReview(Payment payment);

    /**
     * Sends a payment receipt to the customer.
     * @param payment the payment to send receipt for
     */
    void sendReceipt(Payment payment);
}
