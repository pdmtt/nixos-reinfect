resource "digitalocean_ssh_key" "this" {
  count      = var.provider_name == "digitalocean" ? 1 : 0
  name       = "${var.vm_name}-${var.run_id}"
  public_key = var.ssh_public_key
}

resource "digitalocean_droplet" "this" {
  count    = var.provider_name == "digitalocean" ? 1 : 0
  name     = "${var.vm_name}-${var.run_id}"
  image    = var.image
  size     = var.size
  region   = var.region
  ssh_keys = [digitalocean_ssh_key.this[0].fingerprint]

  tags = ["nixos-infect-test", "run-${var.run_id}"]
}
