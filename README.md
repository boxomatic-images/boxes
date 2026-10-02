# Boxomatic Images

## About

Boxomatic provides pre-built Vagrant boxes for development, testing, and educational environments.

The boxes are built using Packer and distributed through GitHub Releases, with Vagrant metadata published through GitHub Pages.

## Available images

See [`docs`](https://boxomatic-images.github.io/boxes/) for the complete list of available images and their descriptions.

## Using an image with Vagrant

A Vagrantfile can reference the image catalog directly:

```ruby
Vagrant.configure("2") do |config|
  config.vm.box = "https://boxomatic-images.github.io/boxes/alpine-3.24.json"
end
```

The provider can then be selected normally:

```ruby
Vagrant.configure("2") do |config|
  config.vm.box = "https://boxomatic-images.github.io/boxes/alpine-3.24.json"

  config.vm.provider "virtualbox"
end
```

or:

```ruby
Vagrant.configure("2") do |config|
  config.vm.box = "https://boxomatic-images.github.io/boxes/alpine-3.24.json"

  config.vm.provider "libvirt"
end
```

Selecting a specific version

A specific box version can be selected with box_version:

```ruby
Vagrant.configure("2") do |config|
  config.vm.box = "https://boxomatic-images.github.io/boxes/alpine-3.24.json"
  config.vm.box_version = "20260930.0.1"
end
```

This allows a Vagrant environment to remain pinned to a specific image version instead of automatically using a newer version.

## Providers

Boxes may be available for different Vagrant providers, depending on the image.

Currently supported providers include:

* VirtualBox
* libvirt

The metadata catalog identifies which providers and architectures are available for each version.

## Releases

Each box version is published as a GitHub Release.

A typical release contains the box itself and a Vagrantfile example:

```
alpine-3.24-amd64-virtualbox-v20260930.0.1
├── boxomatic-alpine-3.24-amd64-virtualbox.box
└── boxomatic-alpine-3.24-amd64-virtualbox.vagrantfile
```

The Vagrantfile included with a release is configured for that specific image, provider, and version.

## Licensing

The licensing terms of the individual operating system images and their included software are determined by their respective upstream projects.

Boxomatic does not replace or modify the licenses of the operating systems and software included in these images.

Each image may contain software distributed under different licenses. Users are responsible for reviewing and complying with the applicable licenses of the included software.

## Disclaimer

These images are provided for educational, development, testing, and research purposes.

They are built automatically from publicly available operating system distributions and software packages. Boxomatic does not claim ownership of the operating systems, packages, trademarks, or other third-party software included in these images.

These images are provided "as is", without warranties of any kind. No guarantee is made regarding their security, suitability, availability, correctness, or fitness for a particular purpose.

Users are responsible for reviewing the contents of an image and ensuring that its use complies with the applicable licenses, terms, and policies of the respective operating system and software vendors.

Do not use these images in production environments unless you have independently reviewed and validated them for your specific requirements.
