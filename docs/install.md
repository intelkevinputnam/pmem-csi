# Instructions for Admins and Users

- [Prerequisites](#prerequisites)
    - [Software required](#software-required)
    - [Hardware required](#hardware-required)
    - [Persistent memory pre-provisioning](#persistent-memory-pre-provisioning)
- [Installation and setup](#installation-and-setup)
    - [Get source code](#get-source-code)
    - [Run PMEM-CSI on Kubernetes](#run-pmem-csi-on-kubernetes)
      - [Expose persistent and cache volumes to applications](#expose-persistent-and-cache-volumes-to-applications)
      - [Raw block volumes](#raw-block-volumes)
      - [Enable scheduler extensions](#enable-scheduler-extensions)
- [Filing issues and contributing](#filing-issues-and-contributing)

## Prerequisites

### Software required

The recommended mimimum Linux kernel version for running the PMEM-CSI driver is 4.15. See [Persistent Memory Programming](https://pmem.io/2018/05/15/using_persistent_memory_devices_with_the_linux_device_mapper.html) for more details about supported kernel versions.

### Hardware required

Persistent memory device(s) are required for operation. However, some
development and testing can be done using QEMU-emulated persistent
memory devices. See the ["QEMU and Kubernetes"](autotest.md#qemu-and-kubernetes)
section for the commands that create such a virtual test cluster.

### Persistent memory pre-provisioning

The PMEM-CSI driver needs pre-provisioned regions on the NVDIMM
device(s). The PMEM-CSI driver itself intentionally leaves that to the
administrator who then can decide how much and how PMEM is to be used
for PMEM-CSI.

Beware that the PMEM-CSI driver will run without errors on a node
where PMEM was not prepared for it. It will then report zero local
storage for that node, something that currently is only visible in the
log files.

When running the Kubernetes cluster and PMEM-CSI on bare metal,
the [ipmctl](https://github.com/intel/ipmctl) utility can be used to create regions.
App Direct Mode has two configuration options - interleaved or non-interleaved.
One region per each NVDIMM is created in non-interleaved configuration.
In such a configuration, a PMEM-CSI volume cannot be larger than one NVDIMM.

Example of creating regions without interleaving, using all NVDIMMs:
```sh
# ipmctl create -goal PersistentMemoryType=AppDirectNotInterleaved
```

Alternatively, multiple NVDIMMs can be combined to form an interleaved set.
This causes the data to be striped over multiple NVDIMM devices
for improved read/write performance and allowing one region (also, PMEM-CSI volume)
to be larger than single NVDIMM.

Example of creating regions in interleaved mode, using all NVDIMMs:
```sh
# ipmctl create -goal PersistentMemoryType=AppDirect
```

When running inside virtual machines, each virtual machine typically
already gets access to one region and `ipmctl` is not needed inside
the virtual machine. Instead, that region must be made available for
use with PMEM-CSI because when the virtual machine comes up for the
first time, the entire region is already allocated for use as a single
block device:
``` sh
# ndctl list -RN
{
  "regions":[
    {
      "dev":"region0",
      "size":34357641216,
      "available_size":0,
      "max_available_extent":0,
      "type":"pmem",
      "persistence_domain":"unknown",
      "namespaces":[
        {
          "dev":"namespace0.0",
          "mode":"raw",
          "size":34357641216,
          "sector_size":512,
          "blockdev":"pmem0"
        }
      ]
    }
  ]
}
# ls -l /dev/pmem*
brw-rw---- 1 root disk 259, 0 Jun  4 16:41 /dev/pmem0
```

Labels must be initialized in such a region, which must be performed
once after the first boot:
``` sh
# ndctl disable-region region0
disabled 1 region
# ndctl init-labels nmem0
initialized 1 nmem
# ndctl enable-region region0
enabled 1 region
# ndctl list -RN
[
  {
    "dev":"region0",
    "size":34357641216,
    "available_size":34357641216,
    "max_available_extent":34357641216,
    "type":"pmem",
    "iset_id":10248187106440278,
    "persistence_domain":"unknown"
  }
]
# ls -l /dev/pmem*
ls: cannot access '/dev/pmem*': No such file or directory
```

## Installation and setup

### Get source code

PMEM-CSI uses Go modules and thus can be checked out and (if that should be desired)
built anywhere in the filesystem. Pre-built container images are available and thus
users don't need to build from source, but they will still need some additional files.
To get the source code, use:

```
git clone https://github.com/intel/pmem-csi
```

### Run PMEM-CSI on Kubernetes

This section assumes that a Kubernetes cluster is already available
with at least one node that has persistent memory device(s). For development or
testing, it is also possible to use a cluster that runs on QEMU virtual
machines, see the ["QEMU and Kubernetes"](autotest.md#qemu-and-kubernetes).

- **Make sure that the alpha feature gates CSINodeInfo and CSIDriverRegistry are enabled**

The method to configure alpha feature gates may vary, depending on the Kubernetes deployment.
It may not be necessary anymore when the feature has reached beta state, which depends
on the Kubernetes version.

- **Label the cluster nodes that provide persistent memory device(s)**

```sh
    $ kubectl label node <your node> storage=pmem
```

- **Set up certificates**

Certificates are required as explained in [Security](design.md#security).
If you are not using the test cluster described in
[Starting and stopping a test cluster](autotest.md#starting-and-stopping-a-test-cluster)
where certificates are created automatically, you must set up certificates manually.
This can be done by running the `./test/setup-ca-kubernetes.sh` script for your cluster.
This script requires "cfssl" tools which can be downloaded.
These are the steps for manual set-up of certificates:

- Download cfssl tools

```sh
   $ curl -L https://pkg.cfssl.org/R1.2/cfssl_linux-amd64 -o _work/bin/cfssl --create-dirs
   $ curl -L https://pkg.cfssl.org/R1.2/cfssljson_linux-amd64 -o _work/bin/cfssljson --create-dirs
   $ chmod a+x _work/bin/cfssl _work/bin/cfssljson
```

- Run certificates set-up script

```sh
   $ KUBCONFIG="<<your cluster kubeconfig path>> PATH="$PATH:$PWD/_work/bin" ./test/setup-ca-kubernetes.sh
```

- **Deploy the driver to Kubernetes**

The `deploy/kubernetes-<kubernetes version>` directory contains
`pmem-csi*.yaml` files which can be used to deploy the driver on that
Kubernetes version. The files in the directory with the highest
Kubernetes version might also work for more recent Kubernetes
releases. All of these deployments use images published by Intel on
[Docker Hub](https://hub.docker.com/u/intel).

For each Kubernetes version, four different deployment variants are provided:

   - `direct` or `lvm`: one uses direct device mode, the other LVM device mode.
   - `testing`: the variants with `testing` in the name enable debugging
     features and shouldn't be used in production.

For example, to deploy for production with LVM device mode onto Kubernetes 1.14, use:

```sh
    $ kubectl create -f deploy/kubernetes-1.14/pmem-csi-lvm.yaml
```

The PMEM-CSI [scheduler extender](design.md#scheduler-extender) and
[webhook](design.md#pod-admission-webhook) are not enabled in this basic
installation. See [below](#enable-scheduler-extensions) for
instructions about that.

These variants were generated with
[`kustomize`](https://github.com/kubernetes-sigs/kustomize).
`kubectl` >= 1.14 includes some support for that. The sub-directories
of [deploy/kustomize](/deploy/kustomize)`-<kubernetes version>` can be used as bases
for `kubectl kustomize`. For example:

   - Change namespace:
     ```
     $ mkdir -p my-pmem-csi-deployment
     $ cat >my-pmem-csi-deployment/kustomization.yaml <<EOF
     namespace: pmem-csi
     bases:
       - ../deploy/kubernetes-1.14/lvm
     EOF
     $ kubectl create namespace pmem-csi
     $ kubectl create --kustomize my-pmem-csi-deployment
     ```

   - Configure how much PMEM is used by PMEM-CSI for LVM
     (see [Namespace modes in LVM device mode](design.md#namespace-modes-in-lvm-device-mode)):
     ```
     $ mkdir -p my-pmem-csi-deployment
     $ cat >my-pmem-csi-deployment/kustomization.yaml <<EOF
     bases:
       - ../deploy/kubernetes-1.14/lvm
     patchesJson6902:
       - target:
           group: apps
           version: v1
           kind: DaemonSet
           name: pmem-csi-node
         path: lvm-parameters-patch.yaml
     EOF
     $ cat >my-pmem-csi-deployment/lvm-parameters-patch.yaml <<EOF
     # pmem-ns-init is in the init container #0. Append arguments at the end.
     - op: add
       path: /spec/template/spec/initContainers/0/args/-
       value: "--useforfsdax=90"
     EOF
     $ kubectl create --kustomize my-pmem-csi-deployment
     ```

- **Wait until all pods reach 'Running' status**

```sh
    $ kubectl get pods
    NAME                    READY   STATUS    RESTARTS   AGE
    pmem-csi-node-8kmxf     2/2     Running   0          3m15s
    pmem-csi-node-bvx7m     2/2     Running   0          3m15s
    pmem-csi-controller-0   2/2     Running   0          3m15s
    pmem-csi-node-fbmpg     2/2     Running   0          3m15s
```

- **Verify that the node labels have been configured correctly**

```sh
    $ kubectl get nodes --show-labels
```

The command output must indicate that every node with PMEM has these two labels:
```
pmem-csi.intel.com/node=<NODE-NAME>,storage=pmem
```

If **storage=pmem** is missing, label manually as described above. If
**pmem-csi.intel.com/node** is missing, then double-check that the
alpha feature gates are enabled, that the CSI driver is running on the node,
and that the driver's log output doesn't contain errors.

- **Define two storage classes using the driver**

```sh
    $ kubectl create -f deploy/kubernetes-<kubernetes version>/pmem-storageclass-ext4.yaml
    $ kubectl create -f deploy/kubernetes-<kubernetes version>/pmem-storageclass-xfs.yaml
```

- **Provision two pmem-csi volumes**

```sh
    $ kubectl create -f deploy/kubernetes-<kubernetes version>/pmem-pvc.yaml
```

- **Verify two Persistent Volume Claims have 'Bound' status**

```sh
    $ kubectl get pvc
    NAME                STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS       AGE
    pmem-csi-pvc-ext4   Bound    pvc-f70f7b36-6b36-11e9-bf09-deadbeef0100   4Gi        RWO            pmem-csi-sc-ext4   16s
    pmem-csi-pvc-xfs    Bound    pvc-f7101fd2-6b36-11e9-bf09-deadbeef0100   4Gi        RWO            pmem-csi-sc-xfs    16s
```

- **Start two applications requesting one provisioned volume each**

```sh
    $ kubectl create -f deploy/kubernetes-<kubernetes version>/pmem-app.yaml
```

These applications use **storage: pmem** in the <i>nodeSelector</i>
list to ensure scheduling to a node supporting pmem device, and each requests a mount of a volume,
one with ext4-format and another with xfs-format file system.

- **Verify two application pods reach 'Running' status**

```sh
    $ kubectl get po my-csi-app-1 my-csi-app-2
    NAME           READY   STATUS    RESTARTS   AGE
    my-csi-app-1   1/1     Running   0          6m5s
    NAME           READY   STATUS    RESTARTS   AGE
    my-csi-app-2   1/1     Running   0          6m1s
```

- **Check that applications have a pmem volume mounted with added dax option**

```sh
    $ kubectl exec my-csi-app-1 -- df /data
    Filesystem           1K-blocks      Used Available Use% Mounted on
    /dev/ndbus0region0fsdax/5ccaa889-551d-11e9-a584-928299ac4b17
                           4062912     16376   3820440   0% /data
    $ kubectl exec my-csi-app-2 -- df /data
    Filesystem           1K-blocks      Used Available Use% Mounted on
    /dev/ndbus0region0fsdax/5cc9b19e-551d-11e9-a584-928299ac4b17
                           4184064     37264   4146800   1% /data

    $ kubectl exec my-csi-app-1 -- mount |grep /data
    /dev/ndbus0region0fsdax/5ccaa889-551d-11e9-a584-928299ac4b17 on /data type ext4 (rw,relatime,dax)
    $ kubectl exec my-csi-app-2 -- mount |grep /data
    /dev/ndbus0region0fsdax/5cc9b19e-551d-11e9-a584-928299ac4b17 on /data type xfs (rw,relatime,attr2,dax,inode64,noquota)
```

#### Expose persistent and cache volumes to applications

Kubernetes cluster administrators can expose persistent and cache volumes
to applications using
[`StorageClass
Parameters`](https://kubernetes.io/docs/concepts/storage/storage-classes/#parameters). An
optional `persistencyModel` parameter differentiates how the
provisioned volume can be used:

* no `persistencyModel` parameter or `persistencyModel: normal` in `StorageClass`  

  A normal Kubernetes persistent volume. In this case
  PMEM-CSI creates PMEM volume on a node and the application that
  claims to use this volume is supposed to be scheduled onto this node
  by Kubernetes. Choosing of node is depend on StorageClass
  `volumeBindingMode`. In case of `volumeBindingMode: Immediate`
  PMEM-CSI chooses a node randomly, and in case of `volumeBindingMode:
  WaitForFirstConsumer` (also known as late binding) Kubernetes first chooses a node for scheduling
  the application, and PMEM-CSI creates the volume on that
  node. Applications which claim a normal persistent volume has to use
  `ReadOnlyOnce` access mode in its `accessModes` list. This
  [diagram](/docs/images/sequence/pmem-csi-persistent-sequence-diagram.png)
  illustrates how a normal persistent volume gets provisioned in
  Kubernetes using PMEM-CSI driver.

* `persistencyModel: cache`  

  Volumes of this type shall be used in combination with
  `volumeBindingMode: Immediate`. In this case, PMEM-CSI creates a set
  of PMEM volumes each volume on different node. The number of PMEM
  volumes to create can be specified by `cacheSize` StorageClass
  parameter. Applications which claim a `cache` volume can use
  `ReadWriteMany` in its `accessModes` list. Check with provided 
  [cacheStorageClass](/deploy/common/pmem-storageclass-cache.yaml)
  example. This
  [diagram](/docs/images/sequence/pmem-csi-cache-sequence-diagram.png)
  illustrates how a cache volume gets provisioned in Kubernetes using
  PMEM-CSI driver.

**NOTE**: Cache volumes are associated with a node, not a pod. Multiple
pods using the same cache volume on the same node will not get their
own instance but will end up sharing the same PMEM volume instead.
Application deployment has to consider this and use available Kubernetes
mechanisms like [node
anti-affinity](https://kubernetes.io/docs/concepts/configuration/assign-pod-node/#affinity-and-anti-affinity).
Check with the provided 
[cacheapplication](/deploy/common/pmem-app-cache.yaml) example.

**WARNING**: late binding (`volumeBindingMode:WaitForFirstConsume`) has some caveats:
* Pod creation may get stuck when there isn't enough capacity left for
  the volumes; see the next section for details.
* A node is only chosen the first time a pod starts. After that it will always restart
  on that node, because that is where the persistent volume was created.

Volume requests embedded in Pod spec are provisioned as ephemeral volumes. The volume request could use below fields as [`volumeAttributes`](https://kubernetes.io/docs/concepts/storage/volumes/#csi):

|key|meaning|optional|values|
|---|-------|--------|-------------|
|`size`|Size of the requested ephemeral volume as [Kubernetes memory string](https://kubernetes.io/docs/concepts/configuration/manage-compute-resources-container/#meaning-of-memory) ("1Mi" = 1024*1024 bytes, "1e3K = 1000000 bytes)|No||
|`eraseAfter`|Clear all data after use and before<br> deleting the volume|Yes|`true` (default),<br> `false`|

Check with provided [example application](/deploy/kubernetes-1.15/pmem-app-ephemeral.yaml) for
ephemeral volume usage.

#### Raw block volumes

Applications can use volumes provisioned by PMEM-CSI as [raw block
devices](https://kubernetes.io/blog/2019/03/07/raw-block-volume-support-to-beta/). Such
volumes use the same "fsdax" namespace mode as filesystem volumes
and therefore are block devices. That mode only supports dax (=
`mmap(MAP_SYNC)`) through a filesystem. Pages mapped on the raw block
device go through the Linux page cache. Applications have to format
and mount the raw block volume themselves if they want dax. The
advantage then is that they have full control over that part.

For provisioning a PMEM volume as raw block device, one has to create a 
`PersistentVolumeClaim` with `volumeMode: Block`. See example [PVC](
/deploy/common/pmem-pvc-block-volume.yaml) and
[application](/deploy/common/pmem-app-block-volume.yaml) for usage reference.

That example demonstrates how to handle some details:
- `mkfs.ext4` needs `-b 4096` to produce volumes that support dax;
  without it, the automatic block size detection may end up choosing
  an unsuitable value depending on the volume size.
- [Kubernetes bug #85624](https://github.com/kubernetes/kubernetes/issues/85624)
  must be worked around to format and mount the raw block device.

#### Enable scheduler extensions

The PMEM-CSI scheduler extender and admission webhook are provided by
the PMEM-CSI controller. They need to be enabled during deployment via
the `--schedulerListen=[<listen address>]:<port>` parameter. The
listen address is optional and can be left out. The port is where a
HTTPS server will run. It uses the same certificates as the internal
gRPC service. When using the CA creation script described above, they
will contain alternative names for the URLs described in this section
(service names, `127.0.0.1` IP address).

This parameter can be added to one of the existing deployment files
with `kustomize`. All of the following examples assume that the
current directory contains the `deploy` directory from the PMEM-CSI
repository. It is also possible to reference the base via a
[URL](https://github.com/kubernetes-sigs/kustomize/blob/master/examples/remoteBuild.md).

``` sh
mkdir my-pmem-csi-deployment

cat >my-pmem-csi-deployment/kustomization.yaml <<EOF
bases:
  - ../deploy/kubernetes-1.16/lvm
patchesJson6902:
  - target:
      group: apps
      version: v1
      kind: StatefulSet
      name: pmem-csi-controller
    path: scheduler-patch.yaml
EOF

cat >my-pmem-csi-deployment/scheduler-patch.yaml <<EOF
- op: add
  path: /spec/template/spec/containers/0/command/-
  value: "--schedulerListen=:8000"
EOF

kubectl create --kustomize my-pmem-csi-deployment
```

To enable the PMEM-CSI scheduler extender, a configuration file and an
additional `--config` parameter for `kube-scheduler` must be added to
the cluster control plane, or, if there is already such a
configuration file, one new entry must be added to the `extenders`
array. A full example is presented below.

The `kube-scheduler` must be able to connect to the PMEM-CSI
controller via the `urlPrefix` in its configuration. In some clusters
it is possible to use cluster DNS and thus a symbolic service name. If
that is the case, then deploy the [scheduler
service](/deploy/kustomize/scheduler/scheduler-service.yaml) as-is
and use `https://pmem-csi-scheduler.default.svc` as `urlPrefix`. If
the PMEM-CSI driver is deployed in a namespace, replace `default` with
the name of that namespace.

In a cluster created with kubeadm, `kube-scheduler` is unable to use
cluster DNS because the pod it runs in is configured with
`hostNetwork: true` and without `dnsPolicy`. Therefore the cluster DNS
servers are ignored. There also is no special dialer as in other
clusters. As a workaround, the PMEM-CSI service can be exposed via a
fixed node port like 32000 on all nodes. Then
`https://127.0.0.1:32000` needs to be used as `urlPrefix`. Here's how
the service can be created with that node port:

``` sh
mkdir my-scheduler

cat >my-scheduler/kustomization.yaml <<EOF
bases:
  - ../deploy/kustomize/scheduler
patchesJson6902:
  - target:
      version: v1
      kind: Service
      name: pmem-csi-scheduler
    path: node-port-patch.yaml
EOF

cat >my-scheduler/node-port-patch.yaml <<EOF
- op: add
  path: /spec/ports/0/nodePort
  value: 32000
EOF

kubectl create --kustomize my-scheduler
```

How to (re)configure `kube-scheduler` depends on the cluster. With
kubeadm it is possible to set all necessary options in advance before
creating the master node with `kubeadm init`. One additional
complication with kubeadm is that `kube-scheduler` by default doesn't
trust any root CA. The following kubeadm config file solves
this together with enabling the scheduler configuration by
bind-mounting the root certificate that was used to sign the certificate used
by the scheduler extender into the location where the Go
runtime will find it:

``` sh
sudo mkdir -p /var/lib/scheduler/
sudo cp _work/pmem-ca/ca.pem /var/lib/scheduler/ca.crt

sudo sh -c 'cat >/var/lib/scheduler/scheduler-policy.cfg' <<EOF
{
  "kind" : "Policy",
  "apiVersion" : "v1",
  "extenders" :
    [{
      "urlPrefix": "https://<service name or IP>:<port>",
      "filterVerb": "filter",
      "prioritizeVerb": "prioritize",
      "nodeCacheCapable": false,
      "weight": 1,
      "managedResources":
      [{
        "name": "pmem-csi.intel.com/scheduler",
        "ignoredByScheduler": true
      }]
    }]
}
EOF

cat >kubeadm.config <<EOF
apiVersion: kubeadm.k8s.io/v1beta1
kind: ClusterConfiguration
scheduler:
  extraVolumes:
    - name: config
      hostPath: /var/lib/scheduler
      mountPath: /var/lib/scheduler
      readOnly: true
    - name: cluster-root-ca
      hostPath: /var/lib/scheduler/ca.crt
      mountPath: /etc/ssl/certs/ca.crt
      readOnly: true
  extraArgs:
    config: /var/lib/scheduler/scheduler-config.yaml
EOF

kubeadm init --config=kubeadm.config
```

It is possible to stop here without enabling the pod admission webhook.
To enable also that, continue as follows.

First of all, it is recommended to exclude all system pods from
passing through the web hook. This ensures that they can still be
created even when PMEM-CSI is down:

``` sh
kubectl label ns kube-system pmem-csi.intel.com/webhook=ignore
```

This special label is configured in [the provided web hook
definition](/deploy/kustomize/webhook/webhook.yaml). On Kubernetes >=
1.15, it can also be used to let individual pods bypass the webhook by
adding that label. The CA gets configured explicitly, which is
supported for webhooks.

``` sh
mkdir my-webhook

cat >my-webhook/kustomization.yaml <<EOF
bases:
  - ../deploy/kustomize/webhook
patchesJson6902:
  - target:
      group: admissionregistration.k8s.io
      version: v1beta1
      kind: MutatingWebhookConfiguration
      name: pmem-csi-hook
    path: webhook-patch.yaml
EOF

cat >my-webhook/webhook-patch.yaml <<EOF
- op: replace
  path: /webhooks/0/clientConfig/caBundle
  value: $(base64 -w 0 _work/pmem-ca/ca.pem)
EOF

kubectl create --kustomize my-webhook
```
<!-- FILL TEMPLATE:

  ### How to extend the plugin

You can modify PMEM-CSI to support more xxx by changing the `variable` from Y to Z.


  ## Maintenance

* Known limitations
* What is supported and what isn't supported
    * Disclaimer that nothing is supported with any kind of SLA
* Example configuration for target use case
* How to upgrade
* Upgrade cadence


  ## Troubleshooting

* If you see this error, then enter this command `blah`.
-->

## Filing issues and contributing

Report a bug by [filing a new issue](https://github.com/intel/pmem-csi/issues).

Before making your first contribution, be sure to read the [development documentation](DEVELOPMENT.md)
for guidance on code quality and branches.

Contribute by [opening a pull request](https://github.com/intel/pmem-csi/pulls).

Learn [about pull requests](https://help.github.com/articles/using-pull-requests/).

**Reporting a Potential Security Vulnerability:** If you have discovered potential security vulnerability in PMEM-CSI, please send an e-mail to secure@intel.com. For issues related to Intel Products, please visit [Intel Security Center](https://security-center.intel.com).

It is important to include the following details:

- The projects and versions affected
- Detailed description of the vulnerability
- Information on known exploits

Vulnerability information is extremely sensitive. Please encrypt all security vulnerability reports using our [PGP key](https://www.intel.com/content/www/us/en/security-center/pgp-public-key.html).

A member of the Intel Product Security Team will review your e-mail and contact you to collaborate on resolving the issue. For more information on how Intel works to resolve security issues, see: [vulnerability handling guidelines](https://www.intel.com/content/www/us/en/security-center/vulnerability-handling-guidelines.html).

<!-- FILL TEMPLATE:
Contact the development team (*TBD: slack or email?*)


  ## References

Pointers to other useful documentation.

* Video tutorial
    * Simple youtube style. Demo installation following steps in readme.
      Useful to show relevant paths. Helps with troubleshooting.
-->
