package preview

import (
	"fmt"
	"net/http"
)

type previewClient struct {
	port int
}

func newPreviewClient(port int) *previewClient {
	return &previewClient{port: port}
}

func (c *previewClient) requestRerun() {
	url := fmt.Sprintf("http://127.0.0.1:%d/rerun", c.port)
	_, _ = http.Post(url, "application/json", nil)
}
