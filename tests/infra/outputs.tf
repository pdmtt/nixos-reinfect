output "ip_address" {
  description = "Public IPv4 address of the created VM"
  value = (
    var.provider_name == "hetzner"      ? try(hcloud_server.this[0].ipv4_address, "") :
    var.provider_name == "digitalocean" ? try(digitalocean_droplet.this[0].ipv4_address, "") :
    ""
  )
}
