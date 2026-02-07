package main

import (
	"fmt"
	"os"
	"os/exec"
)

var modules = []struct {
	path    string
	version string
}{
	{path: "github.com/google/uuid", version: "v1.6.0"},
	{path: "github.com/lib/pq", version: "v1.10.9"},
	{path: "golang.org/x/crypto", version: "v0.46.0"},
}

func main() {
	fmt.Println("Installing Go module dependencies...")
	for _, mod := range modules {
		if err := goGet(mod.path, mod.version); err != nil {
			fmt.Fprintf(os.Stderr, "failed to install %s@%s: %v\n", mod.path, mod.version, err)
			os.Exit(1)
		}
	}
	fmt.Println("All Go dependencies installed.")
}

func goGet(path, version string) error {
	fmt.Printf("→ go get %s@%s\n", path, version)
	cmd := exec.Command("go", "get", fmt.Sprintf("%s@%s", path, version))
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}
