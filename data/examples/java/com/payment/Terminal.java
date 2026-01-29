package com.payment;

/**
 * Represents a registered payment terminal (Android device).
 * Terminals must be registered with Chase Gempay before processing tap-to-pay.
 */
public class Terminal {

    private String terminalId;
    private String deviceId;
    private String deviceName;
    private String merchantId;
    private TerminalStatus status;
    private long registeredAt;
    private long lastActiveAt;
    private String softwareVersion;
    private TerminalCapabilities capabilities;

    public Terminal() {
        this.status = TerminalStatus.PENDING;
    }

    public Terminal(String terminalId, String deviceId, String deviceName, String merchantId) {
        this.terminalId = terminalId;
        this.deviceId = deviceId;
        this.deviceName = deviceName;
        this.merchantId = merchantId;
        this.status = TerminalStatus.PENDING;
    }

    /**
     * Checks if the terminal is registered and active.
     * @return true if terminal can process payments
     */
    public boolean isRegistered() {
        return terminalId != null && status == TerminalStatus.ACTIVE;
    }

    /**
     * Checks if the terminal can process tap-to-pay transactions.
     * @return true if tap-to-pay capable
     */
    public boolean canProcessTapToPay() {
        return isRegistered() &&
               capabilities != null &&
               capabilities.isNfcEnabled();
    }

    /**
     * Updates the last active timestamp.
     */
    public void markActive() {
        this.lastActiveAt = System.currentTimeMillis();
    }

    /**
     * Deactivates the terminal.
     */
    public void deactivate() {
        this.status = TerminalStatus.INACTIVE;
    }

    // Getters and setters
    public String getTerminalId() { return terminalId; }
    public void setTerminalId(String terminalId) { this.terminalId = terminalId; }

    public String getDeviceId() { return deviceId; }
    public void setDeviceId(String deviceId) { this.deviceId = deviceId; }

    public String getDeviceName() { return deviceName; }
    public void setDeviceName(String deviceName) { this.deviceName = deviceName; }

    public String getMerchantId() { return merchantId; }
    public void setMerchantId(String merchantId) { this.merchantId = merchantId; }

    public TerminalStatus getStatus() { return status; }
    public void setStatus(TerminalStatus status) { this.status = status; }

    public long getRegisteredAt() { return registeredAt; }
    public void setRegisteredAt(long registeredAt) { this.registeredAt = registeredAt; }

    public long getLastActiveAt() { return lastActiveAt; }
    public void setLastActiveAt(long lastActiveAt) { this.lastActiveAt = lastActiveAt; }

    public String getSoftwareVersion() { return softwareVersion; }
    public void setSoftwareVersion(String softwareVersion) { this.softwareVersion = softwareVersion; }

    public TerminalCapabilities getCapabilities() { return capabilities; }
    public void setCapabilities(TerminalCapabilities capabilities) { this.capabilities = capabilities; }
}
