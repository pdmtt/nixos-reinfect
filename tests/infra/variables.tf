variable "provider_name" {
  type        = string
  description = "Which provider to use: hetzner, digitalocean"
}

variable "image" {
  type        = string
  description = "OS image identifier (provider-specific)"
}

variable "region" {
  type        = string
  description = "Provider region/location"
}

variable "size" {
  type        = string
  description = "Instance size/type (provider-specific)"
}

variable "ssh_public_key" {
  type        = string
  description = "SSH public key content to inject into the VM"
}

variable "run_id" {
  type        = string
  default     = ""
  description = "GitHub Actions run ID, used for resource tagging"
}

variable "vm_name" {
  type        = string
  default     = "nixos-infect-test"
  description = "VM name prefix"
}
