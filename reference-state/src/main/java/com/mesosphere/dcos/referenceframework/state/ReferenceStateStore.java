package com.mesosphere.dcos.referenceframework.state;

import org.apache.mesos.Protos;
import org.apache.mesos.reconciliation.TaskStatusProvider;

import java.util.Observable;
import java.util.Observer;
import java.util.Set;

public class ReferenceStateStore implements Observer, TaskStatusProvider {

    @Override
    public void update(Observable o, Object arg) {

    }

    @Override
    public Set<Protos.TaskStatus> getTaskStatuses() throws Exception {
        return null;
    }
}
