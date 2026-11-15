# Läuft in GitHub Actions: versucht, den kostenlosen ARM-Server anzulegen.
# Alle Zugangsdaten kommen aus GitHub-Secrets (Umgebungsvariablen).
import os, sys, oci
for k in list(os.environ):
    if k.startswith(("OCI_", "SSH_")):
        os.environ[k] = os.environ[k].replace("\r", "").strip()

cfg = {
    "user": os.environ["OCI_USER"],
    "fingerprint": os.environ["OCI_FINGERPRINT"],
    "tenancy": os.environ["OCI_TENANCY"],
    "region": os.environ["OCI_REGION"],
    "key_content": os.environ["OCI_KEY"],
}
oci.config.validate_config(cfg)
comp_id, ad, subnet = os.environ["OCI_TENANCY"], os.environ["OCI_AD"], os.environ["OCI_SUBNET"]
comp = oci.core.ComputeClient(cfg)

def ergebnis(text):
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f:
        f.write(f"ergebnis={text}\n")

for i in comp.list_instances(comp_id, display_name="server-1").data:
    if i.lifecycle_state not in ("TERMINATED", "TERMINATING"):
        print(f"server-1 existiert bereits ({i.lifecycle_state}).")
        ergebnis("vorhanden")
        sys.exit(0)

image = comp.list_images(comp_id, operating_system="Canonical Ubuntu", operating_system_version="24.04",
                         shape="VM.Standard.A1.Flex", sort_by="TIMECREATED", sort_order="DESC").data[0].id
try:
    comp.launch_instance(oci.core.models.LaunchInstanceDetails(
        compartment_id=comp_id, availability_domain=ad, display_name="server-1",
        shape="VM.Standard.A1.Flex",
        shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(ocpus=2, memory_in_gbs=12),
        source_details=oci.core.models.InstanceSourceViaImageDetails(image_id=image),
        create_vnic_details=oci.core.models.CreateVnicDetails(subnet_id=subnet, assign_public_ip=True),
        metadata={"ssh_authorized_keys": os.environ["SSH_PUBKEY"]}))
    print("ERFOLG: server-1 wird angelegt.")
    ergebnis("erfolg")
except oci.exceptions.ServiceError as e:
    if "capacity" in (e.message or "").lower():
        print("Kein Platz frei, naechster Versuch spaeter.")
        ergebnis("kein-platz")
    else:
        print(f"Anderer Fehler: {e.status} {e.code}")
        ergebnis("fehler")
        sys.exit(1)
