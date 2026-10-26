package com.careeros.support;

import static org.mockito.Mockito.mock;

import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * A {@code TransactionTemplate} that runs the callback and claims nothing else, for the unit
 * tests that build a service by hand and have no database to bind.
 *
 * <p>It is not evidence: the template here decides that the writer runs, not that its rows commit
 * together. That claim belongs to the integration tests, which get it from a real
 * {@code JpaTransactionManager} against the IT schema -- {@code JobImportAtomicityIT} for the
 * import boundary that motivated this helper.
 */
public final class TestTransactions {

    private TestTransactions() {
    }

    public static TransactionTemplate executing() {
        return new TransactionTemplate(mock(PlatformTransactionManager.class));
    }
}
