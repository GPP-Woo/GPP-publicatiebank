.. _installation_helm:

Helm
====

Deploying to Kubernetes is possible with Helm_. The GPP-Woo maintainers publish
`charts <https://github.com/GPP-Woo/charts>`_ for the full stack (umbrella chart) and
the invidual components. You can use the former as-is, or use it as inspiration to build
your own umbrella chart.

The remainder of the documentation assumes you're deploying the full stack.

Requirements
------------

**Persistent storage**

GPP-publicatiebank instances require persistent storage. The Helm charts by default
enable persistence, creating a PVC if none is specified. The PVC must be
``ReadWriteMany`` if you're deploying multiple replicas.

Add the repositories
--------------------

To deploy the charts, first add the necessary repositories:

.. code-block:: bash

    helm repo add gpp-woo https://GPP-Woo.github.io/charts

Deploy the stack
----------------

To deploy the stack, ensure you have your own ``values.yml`` file overriding the relevant
settings/defaults from the chart itself - see
`GitHub <https://github.com/GPP-Woo/charts/tree/main/charts/GPP-stack>`_ for a reference.

.. code-block:: bash

    helm repo update
    helm install \
        -f myvalues.yml \
        my-gpp-woo \
        gpp-woo/gpp-stack

Adapt the name ``my-gpp-woo`` to your liking.

.. _Helm: https://helm.sh/
