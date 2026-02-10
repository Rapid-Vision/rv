// THIS CODE IS GENERATED

package rpcclient

import "fmt"

type RPCErrorType string

const (
	RPCErrorCustom         RPCErrorType = "custom"
	RPCErrorValidation     RPCErrorType = "validation"
	RPCErrorInput          RPCErrorType = "input"
	RPCErrorUnauthorized   RPCErrorType = "unauthorized"
	RPCErrorForbidden      RPCErrorType = "forbidden"
	RPCErrorNotImplemented RPCErrorType = "not_implemented"
)

type RPCError struct {
	Type    RPCErrorType `json:"type"`
	Message string       `json:"message"`
}

type RPCErrorException struct {
	Err RPCError
}

func (e RPCErrorException) Error() string {
	return e.Err.Message
}

type ErrHTTP struct {
	Status int
	Body   string
}

func (e ErrHTTP) Error() string {
	if e.Body == "" {
		return fmt.Sprintf("rpc error: status %d", e.Status)
	}
	return fmt.Sprintf("rpc error: status %d: %s", e.Status, e.Body)
}

type CustomRPCError struct {
	RPCError
}

func (e CustomRPCError) Error() string {
	return e.Message
}

type ValidationRPCError struct {
	RPCError
}

func (e ValidationRPCError) Error() string {
	return e.Message
}

type InputRPCError struct {
	RPCError
}

func (e InputRPCError) Error() string {
	return e.Message
}

type UnauthorizedRPCError struct {
	RPCError
}

func (e UnauthorizedRPCError) Error() string {
	return e.Message
}

type ForbiddenRPCError struct {
	RPCError
}

func (e ForbiddenRPCError) Error() string {
	return e.Message
}

type NotImplementedRPCError struct {
	RPCError
}

func (e NotImplementedRPCError) Error() string {
	return e.Message
}

func errorFromRPCError(err RPCError) error {
	switch err.Type {
	case RPCErrorCustom:
		return CustomRPCError{RPCError: err}
	case RPCErrorValidation:
		return ValidationRPCError{RPCError: err}
	case RPCErrorInput:
		return InputRPCError{RPCError: err}
	case RPCErrorUnauthorized:
		return UnauthorizedRPCError{RPCError: err}
	case RPCErrorForbidden:
		return ForbiddenRPCError{RPCError: err}
	case RPCErrorNotImplemented:
		return NotImplementedRPCError{RPCError: err}
	default:
		return RPCErrorException{Err: err}
	}
}
