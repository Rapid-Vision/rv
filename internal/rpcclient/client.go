// THIS CODE IS GENERATED

package rpcclient

import (
	"net/http"
	"strings"
)

type RPCClient struct {
	baseURL     string
	client      *http.Client
	headers     map[string]string
	bearerToken string
}

func NewRPCClient(baseURL string) *RPCClient {
	return &RPCClient{
		baseURL: strings.TrimRight(baseURL, "/"),
		client:  http.DefaultClient,
		headers: map[string]string{},
	}
}

func (c *RPCClient) WithHTTPClient(client *http.Client) *RPCClient {
	if client == nil {
		client = http.DefaultClient
	}
	next := c.clone()
	next.client = client
	return next
}

func (c *RPCClient) WithHeaders(headers map[string]string) *RPCClient {
	next := c.clone()
	if headers == nil {
		return next
	}
	for key, value := range headers {
		next.headers[key] = value
	}
	return next
}

func (c *RPCClient) WithBearerToken(token string) *RPCClient {
	next := c.clone()
	next.bearerToken = token
	return next
}

func (c *RPCClient) clone() *RPCClient {
	copiedHeaders := make(map[string]string, len(c.headers))
	for key, value := range c.headers {
		copiedHeaders[key] = value
	}
	return &RPCClient{
		baseURL:     c.baseURL,
		client:      c.client,
		headers:     copiedHeaders,
		bearerToken: c.bearerToken,
	}
}
