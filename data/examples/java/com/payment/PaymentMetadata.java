package com.payment;

import java.util.HashMap;
import java.util.Map;

/**
 * Contains additional metadata for a payment transaction.
 * Stores provider-specific data, failure reasons, and custom attributes.
 */
public class PaymentMetadata {

    private String failureReason;
    private String failureCode;
    private String providerTransactionId;
    private String providerName;
    private Map<String, String> customAttributes;
    private String ipAddress;
    private String userAgent;
    private String billingAddress;
    private String shippingAddress;

    public PaymentMetadata() {
        this.customAttributes = new HashMap<>();
    }

    /**
     * Adds a custom attribute to the metadata.
     * @param key the attribute key
     * @param value the attribute value
     */
    public void addAttribute(String key, String value) {
        this.customAttributes.put(key, value);
    }

    /**
     * Gets a custom attribute from the metadata.
     * @param key the attribute key
     * @return the attribute value, or null if not found
     */
    public String getAttribute(String key) {
        return this.customAttributes.get(key);
    }

    /**
     * Checks if the payment has failure information.
     * @return true if there is a failure reason or code
     */
    public boolean hasFailureInfo() {
        return failureReason != null || failureCode != null;
    }

    // Getters and setters
    public String getFailureReason() { return failureReason; }
    public void setFailureReason(String failureReason) { this.failureReason = failureReason; }

    public String getFailureCode() { return failureCode; }
    public void setFailureCode(String failureCode) { this.failureCode = failureCode; }

    public String getProviderTransactionId() { return providerTransactionId; }
    public void setProviderTransactionId(String providerTransactionId) {
        this.providerTransactionId = providerTransactionId;
    }

    public String getProviderName() { return providerName; }
    public void setProviderName(String providerName) { this.providerName = providerName; }

    public Map<String, String> getCustomAttributes() { return customAttributes; }

    public String getIpAddress() { return ipAddress; }
    public void setIpAddress(String ipAddress) { this.ipAddress = ipAddress; }

    public String getUserAgent() { return userAgent; }
    public void setUserAgent(String userAgent) { this.userAgent = userAgent; }

    public String getBillingAddress() { return billingAddress; }
    public void setBillingAddress(String billingAddress) { this.billingAddress = billingAddress; }

    public String getShippingAddress() { return shippingAddress; }
    public void setShippingAddress(String shippingAddress) { this.shippingAddress = shippingAddress; }
}
