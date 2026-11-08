// Command mcp-server is a sample MCP server for the GEAP starter pack mini build.
// It has one read-only tool (get_status) and one write tool (update_status).
// Demo only: the data is in memory.
package main

import (
	"log"
	"net/http"
	"os"
	"time"
)

func listenAddr() string {
	if p := os.Getenv("PORT"); p != "" {
		return ":" + p
	}
	return ":8080"
}

func main() {
	addr := listenAddr()
	srv := &http.Server{
		Addr:              addr,
		Handler:           NewMux(NewServer(NewStore())),
		ReadHeaderTimeout: 10 * time.Second,
	}
	log.Printf("mcp-server: listening on %s", addr)
	log.Fatal(srv.ListenAndServe())
}
