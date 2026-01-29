package com.payment;

/**
 * Status of a payment terminal registration.
 */
public enum TerminalStatus {

    /** Terminal registration is pending approval */
    PENDING,

    /** Terminal is active and can process payments */
    ACTIVE,

    /** Terminal has been deactivated */
    INACTIVE,

    /** Terminal is suspended due to suspicious activity */
    SUSPENDED,

    /** Terminal registration has expired */
    EXPIRED;

    /**
     * Checks if the terminal can process payments.
     * @return true if payments can be processed
     */
    public boolean canProcess() {
        return this == ACTIVE;
    }

    /**
     * Checks if the terminal can be reactivated.
     * @return true if reactivation is possible
     */
    public boolean canReactivate() {
        return this == INACTIVE || this == EXPIRED;
    }
}
