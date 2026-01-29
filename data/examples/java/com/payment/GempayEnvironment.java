package com.payment;

/**
 * Chase Gempay API environments.
 */
public enum GempayEnvironment {

    SANDBOX("https://api-sandbox.chase.com/gempay/v1", true),
    PRODUCTION("https://api.chase.com/gempay/v1", false);

    private final String baseUrl;
    private final boolean testMode;

    GempayEnvironment(String baseUrl, boolean testMode) {
        this.baseUrl = baseUrl;
        this.testMode = testMode;
    }

    public String getBaseUrl() {
        return baseUrl;
    }

    public boolean isTestMode() {
        return testMode;
    }

    /**
     * Gets the appropriate environment based on a flag.
     * @param useProduction true for production, false for sandbox
     * @return the environment
     */
    public static GempayEnvironment fromFlag(boolean useProduction) {
        return useProduction ? PRODUCTION : SANDBOX;
    }
}
