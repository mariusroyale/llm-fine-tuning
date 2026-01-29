package com.payment;

/**
 * Exception thrown when communication with payment gateway fails.
 */
public class PaymentGatewayException extends RuntimeException {

    private final String gatewayName;
    private final String gatewayErrorCode;

    public PaymentGatewayException(String message, String gatewayName) {
        super(message);
        this.gatewayName = gatewayName;
        this.gatewayErrorCode = null;
    }

    public PaymentGatewayException(String message, String gatewayName, String gatewayErrorCode) {
        super(message);
        this.gatewayName = gatewayName;
        this.gatewayErrorCode = gatewayErrorCode;
    }

    public PaymentGatewayException(String message, String gatewayName, Throwable cause) {
        super(message, cause);
        this.gatewayName = gatewayName;
        this.gatewayErrorCode = null;
    }

    public String getGatewayName() {
        return gatewayName;
    }

    public String getGatewayErrorCode() {
        return gatewayErrorCode;
    }
}
