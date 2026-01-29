package com.payment;

/**
 * Status of a transaction at the payment gateway level.
 */
public enum TransactionStatus {

    /** Transaction is awaiting processing */
    PENDING,

    /** Transaction has been approved */
    APPROVED,

    /** Transaction was declined by the issuer */
    DECLINED,

    /** Transaction encountered an error */
    ERROR,

    /** Transaction was voided */
    VOIDED,

    /** Transaction was refunded */
    REFUNDED,

    /** Transaction is in review */
    REVIEW,

    /** Transaction status is unknown */
    UNKNOWN
}
