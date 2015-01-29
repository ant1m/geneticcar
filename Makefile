# VARIABLES
MODULE_NAME="geneticcar"
PACKAGE="gitlab.aql.fr/geneticcar"
BINARY_NAME="geneticcar"
TARGET_DIR="target"
PACKAGING_DIR=$(TARGET_DIR)/package
GO_VERSION="1.4.1"

export GOPATH=$(shell pwd)

# Default target : USAGE
default:
	@echo "You must specify a target with this makefile"
	@echo "Usage : "
	@echo "make clean        Remove binary files"
	@echo "make install      Compile sources and build binaries"
	@echo "make test         Run all tests of your application"
	@echo "make run          Build your application and run it"
	@echo "make develop      Start your favorite ide"
	@echo "make package      Build project tarball"
	@echo "make deploy       Build project tarball and deploy it"
	@echo "make release      Release project, deploy it on IPP and tag it (based on version.properties file)"

# Check go version
checkGoVersion:
	@echo "check if you have the correct golang version ($(GO_VERSION))..."
	@go version | grep $(GO_VERSION) > /dev/null
	@echo "--> checking OK"

# Clean binaries and targets
clean:	checkGoVersion
	@echo "cleaning..."
	@go clean || (echo "Unable to clean project" && exit 1)
	@rm -rf bin/$(BINARY_NAME) 2> /dev/null
	@rm -rf target/* 2> /dev/null
	@rm -rf pkg/* 2> /dev/null
	@echo "--> cleaning OK"

# Test your application
test: clean
	@echo "testing..."
	@go test -v $(PACKAGE)/...
	@echo "--> testing OK"

# Compile sources and build binary
install: clean test
	@echo "installing..."
	@go install $(PACKAGE)
	@echo "--> installing OK"

# Run your application
run: clean install
	@echo "--> running application..."
	@./bin/$(BINARY_NAME) etc/configuration.json

# Start your favorite IDE
develop: 
	@echo "--> starting your favorite IDE..."
	/bin/mygolangide &
	@echo "--> See you!"

# Create IPP archive
package: install
	@echo "creating tarball..."
	$(shell ./misc/ipptools.sh package)
	@echo "--> creating package done in target/package"

# Deploy a snapshot on IPP
deploy: install
	@echo "deploying a snapshot on IPP..."
	$(shell misc/ipptools.sh deploy dev > /dev/null)
	@echo "--> deploying OK"

# Release, tag and deploy project on integration IPP environment
release: install
	@echo "releasing your project on integration environment..."
	$(shell ./misc/ipptools.sh release)
	@echo "--> releasing done"
