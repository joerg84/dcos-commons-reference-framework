package com.mesosphere.dcos.referenceframework.executor;

import org.apache.mesos.ExecutorDriver;
import org.apache.mesos.Protos;
import org.apache.mesos.executor.CustomExecutor;
import org.apache.mesos.executor.ExecutorDriverFactory;
import org.apache.mesos.executor.MesosExecutorDriverFactory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class Main {
    private static final Logger LOGGER = LoggerFactory.getLogger(Main.class);

    public static void main(String[] args) throws Exception {
        start(new MesosExecutorDriverFactory());
    }

    public static void start(ExecutorDriverFactory executorDriverFactory) {
        final ExecutorService executorService = Executors.newCachedThreadPool();
        final ReferenceFrameworkExecutorTaskFactory referenceFrameworkExecutorTaskFactory = new ReferenceFrameworkExecutorTaskFactory();
        final CustomExecutor referenceFrameworkExecutor = new CustomExecutor(executorService, referenceFrameworkExecutorTaskFactory);
        final ExecutorDriver driver = executorDriverFactory.getDriver(referenceFrameworkExecutor);
        final Protos.Status status = driver.run();


        LOGGER.info("Driver stopped: status = {}", status);
        System.exit(0);
    }
}
