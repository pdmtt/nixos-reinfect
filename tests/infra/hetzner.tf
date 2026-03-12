resource "hcloud_ssh_key" "this" {
  count      = var.provider_name == "hetzner" ? 1 : 0
  name       = "${var.vm_name}-${var.run_id}-${replace(var.image, "/", "-")}"
  public_key = var.ssh_public_key
}

resource "hcloud_server" "this" {
  count       = var.provider_name == "hetzner" ? 1 : 0
  name        = "${var.vm_name}-${var.run_id}"
  image       = var.image
  server_type = var.size
  location    = var.region
  ssh_keys    = [hcloud_ssh_key.this[0].id]

  labels = {
    purpose = "nixos-infect-test"
    run_id  = var.run_id
  }
}
