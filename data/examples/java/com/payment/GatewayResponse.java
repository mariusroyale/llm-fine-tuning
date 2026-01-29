package com.payment;

import java.time.LocalDateTime;

/**
 * Represents a response from a payment gateway.
 * Contains transaction details, status, and any error information.
 */
public class GatewayResponse {

    private boolean successful;
    private String transactionId;
    private String authorizationCode;
    private String errorCode;
    private String errorMessage;
    private TransactionStatus status;
    private LocalDateTime timestamp;
    private String rawResponse;

    private GatewayResponse() {
        this.timestamp = LocalDateTime.now();
    }

    /**
     * Creates a successful gateway response.
     * @param transactionId the transaction ID from the provider
     * @param authorizationCode the authorization code
     * @return successful response
     */
    public static GatewayResponse success(String transactionId, String authorizationCode) {
        GatewayResponse response = new GatewayResponse();
        response.successful = true;
        response.transactionId = transactionId;
        response.authorizationCode = authorizationCode;
        response.status = TransactionStatus.APPROVED;
        return response;
    }

    /**
     * Creates a failed gateway response.
     * @param errorCode the error code
     * @param errorMessage the error description
     * @return failed response
     */
    public static GatewayResponse failure(String errorCode, String errorMessage) {
        GatewayResponse response = new GatewayResponse();
        response.successful = false;
        response.errorCode = errorCode;
        response.errorMessage = errorMessage;
        response.status = TransactionStatus.DECLINED;
        return response;
    }

    /**
     * Creates a pending gateway response for async processing.
     * @param transactionId the pending transaction ID
     * @return pending response
     */
    public static GatewayResponse pending(String transactionId) {
        GatewayResponse response = new GatewayResponse();
        response.successful = false;
        response.transactionId = transactionId;
        response.status = TransactionStatus.PENDING;
        return response;
    }

    public boolean isSuccessful() { return successful; }
    public String getTransactionId() { return transactionId; }
    public String getAuthorizationCode() { return authorizationCode; }
    public String getErrorCode() { return errorCode; }
    public String getErrorMessage() { return errorMessage; }
    public TransactionStatus getStatus() { return status; }
    public LocalDateTime getTimestamp() { return timestamp; }

    public String getRawResponse() { return rawResponse; }
    public void setRawResponse(String rawResponse) { this.rawResponse = rawResponse; }
}
