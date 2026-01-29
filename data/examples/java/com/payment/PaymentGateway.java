package com.payment;

import java.math.BigDecimal;

/**
 * Interface for payment gateway integrations.
 * Abstracts the communication with external payment providers.
 */
public interface PaymentGateway {

    /**
     * Charges a payment through the gateway.
     * @param payment the payment to charge
     * @return the gateway response
     * @throws PaymentGatewayException if communication fails
     */
    GatewayResponse charge(Payment payment) throws PaymentGatewayException;

    /**
     * Refunds a previously charged payment.
     * @param transactionId the original transaction ID
     * @param amount the amount to refund
     * @return the gateway response
     * @throws PaymentGatewayException if communication fails
     */
    GatewayResponse refund(String transactionId, BigDecimal amount) throws PaymentGatewayException;

    /**
     * Voids an authorized but not captured payment.
     * @param transactionId the transaction to void
     * @return the gateway response
     * @throws PaymentGatewayException if communication fails
     */
    GatewayResponse voidTransaction(String transactionId) throws PaymentGatewayException;

    /**
     * Checks the status of a transaction.
     * @param transactionId the transaction ID
     * @return the current transaction status
     */
    TransactionStatus getTransactionStatus(String transactionId);

    /**
     * Tests connectivity with the gateway.
     * @return true if gateway is reachable
     */
    boolean healthCheck();

    /**
     * Gets the name of this gateway provider.
     * @return the provider name
     */
    String getProviderName();
}
