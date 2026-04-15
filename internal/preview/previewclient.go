package preview

import (
	"fmt"
	"net/http"

	"github.com/Rapid-Vision/rv/internal/logs"
)

type previewClient struct {
	port int
}

func newPreviewClient(port int) *previewClient {
	return &previewClient{port: port}
}

func (c *previewClient) requestRerun() {
	url := fmt.Sprintf("http://127.0.0.1:%d/rerun", c.port)
	resp, err := http.Post(url, "application/json", nil)
	if err != nil {
		logs.Warn.Println("Failed to request preview rerun:", err)
		return
	}
	defer func() { _ = resp.Body.Close() }()

	if resp.StatusCode != http.StatusOK {
		logs.Warn.Printf("Preview rerun request returned status %d\n", resp.StatusCode)
	}
}
