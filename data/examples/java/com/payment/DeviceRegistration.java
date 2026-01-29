package com.payment;

/**
 * Request object for registering an Android device as a payment terminal.
 * Contains all information needed to register with Chase Gempay.
 */
public class DeviceRegistration {

    private String deviceId;
    private String deviceName;
    private String deviceModel;
    private String deviceManufacturer;
    private String androidVersion;
    private int androidSdkVersion;
    private String appVersion;
    private String appPackageName;
    private TerminalCapabilities capabilities;
    private String merchantId;
    private String locationId;
    private String operatorId;

    public DeviceRegistration() {}

    /**
     * Builder for creating device registration requests.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private final DeviceRegistration registration = new DeviceRegistration();

        public Builder deviceId(String deviceId) {
            registration.deviceId = deviceId;
            return this;
        }

        public Builder deviceName(String deviceName) {
            registration.deviceName = deviceName;
            return this;
        }

        public Builder deviceModel(String deviceModel) {
            registration.deviceModel = deviceModel;
            return this;
        }

        public Builder deviceManufacturer(String deviceManufacturer) {
            registration.deviceManufacturer = deviceManufacturer;
            return this;
        }

        public Builder androidVersion(String androidVersion) {
            registration.androidVersion = androidVersion;
            return this;
        }

        public Builder androidSdkVersion(int androidSdkVersion) {
            registration.androidSdkVersion = androidSdkVersion;
            return this;
        }

        public Builder appVersion(String appVersion) {
            registration.appVersion = appVersion;
            return this;
        }

        public Builder appPackageName(String appPackageName) {
            registration.appPackageName = appPackageName;
            return this;
        }

        public Builder capabilities(TerminalCapabilities capabilities) {
            registration.capabilities = capabilities;
            return this;
        }

        public Builder merchantId(String merchantId) {
            registration.merchantId = merchantId;
            return this;
        }

        public Builder locationId(String locationId) {
            registration.locationId = locationId;
            return this;
        }

        public Builder operatorId(String operatorId) {
            registration.operatorId = operatorId;
            return this;
        }

        public DeviceRegistration build() {
            return registration;
        }
    }

    /**
     * Validates that all required fields are present.
     * @return true if valid
     */
    public boolean isValid() {
        return deviceId != null && !deviceId.isEmpty() &&
               merchantId != null && !merchantId.isEmpty() &&
               androidSdkVersion >= 28; // Minimum Android 9
    }

    /**
     * Gets a display name for the device.
     * @return human-readable device identifier
     */
    public String getDisplayName() {
        if (deviceName != null && !deviceName.isEmpty()) {
            return deviceName;
        }
        if (deviceManufacturer != null && deviceModel != null) {
            return deviceManufacturer + " " + deviceModel;
        }
        return deviceId;
    }

    // Getters
    public String getDeviceId() { return deviceId; }
    public String getDeviceName() { return deviceName; }
    public String getDeviceModel() { return deviceModel; }
    public String getDeviceManufacturer() { return deviceManufacturer; }
    public String getAndroidVersion() { return androidVersion; }
    public int getAndroidSdkVersion() { return androidSdkVersion; }
    public String getAppVersion() { return appVersion; }
    public String getAppPackageName() { return appPackageName; }
    public TerminalCapabilities getCapabilities() { return capabilities; }
    public String getMerchantId() { return merchantId; }
    public String getLocationId() { return locationId; }
    public String getOperatorId() { return operatorId; }
}
