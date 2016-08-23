package com.mesosphere.dcos.referenceframework.executor;

import java.util.List;

import org.apache.mesos.ExecutorDriver;
import org.apache.mesos.Protos;
import org.apache.mesos.executor.*;

import java.util.Collections;

public class ReferenceFrameworkExecutorTaskFactory implements ExecutorTaskFactory {
    @Override
    public ExecutorTask createTask(
            final String taskType,
            final Protos.TaskInfo task,
            final ExecutorDriver driver) throws ExecutorTaskException {

        return new ProcessTask(driver, task);
    }


    @Override
    public List<TimedExecutorTask> createTimedTasks(String taskType, Protos.ExecutorInfo executorInfo, ExecutorDriver driver) throws ExecutorTaskException {
        return Collections.emptyList();
    }
}
