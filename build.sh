#!/bin/bash

##	Purpose: Quick and dirty build script until 'redo' build system implemented.
##	History:
##		- 20200927 JC: Created.


function fMain(){

	## Validate
	if [[   -z "$(which basename 2>/dev/null || true)" ]]; then echo; echo "Error: Not found in path: 'basename'"; echo; exit 1; fi
	if [[   -z "$(which dirname  2>/dev/null || true)" ]]; then echo; echo "Error: Not found in path: 'dirname'";  echo; exit 1; fi
	if [[   -z "$(which pwd      2>/dev/null || true)" ]]; then echo; echo "Error: Not found in path: 'pwd'";      echo; exit 1; fi
	if [[   -z "$(which go       2>/dev/null || true)" ]]; then echo; echo "Error: Not found in path: 'go'";       echo; exit 1; fi
	if [[ ! -f "main.go"                               ]]; then echo; echo "Error: Not found: 'main.go'";          echo; exit 1; fi

	## Constants
	local -r exeName="$(basename "$(dirname "$(pwd)")")"

	## Init
	[[ ! -d  bin                  ]] && mkdir  bin
	[[   -f "/tmp/${exeName}_old" ]] && rm    "/tmp/${exeName}_old"
	[[   -f "bin/${exeName}_old"  ]] && mv    "bin/${exeName}_old"  "/tmp/"
	[[   -f "bin/${exeName}"      ]] && mv    "bin/${exeName}"      "bin/${exeName}_old"

	## Build
	echo
	echo "[ Building ... ]"
	echo
	go build -o "bin/${exeName}"

	## Some build examples
	#	GOOS=linux GOARCH=arm GOARM=6 go build -o mybin-arm
	#	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -tags netgo -ldflags '-w' -o mybin *.go
	## Help
	#	-tags netgo  ..............: Use go net package not system
	#	-ldflags '-w'  ............: Disable debug symbols
	#	-extldflags "-static"'  ...: 

	## Test
	echo
	echo "[ Test run ... ]"
	echo "-------------------------------------------------------------------------------"
	bin/${exeName}
	echo "-------------------------------------------------------------------------------"
	echo

}


set -e
set -E
fMain