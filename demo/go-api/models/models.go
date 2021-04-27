package models

// IdentificationDocumentInput represents the IDDocument inputs
type IdentificationDocumentInput struct {
	IDDocType   string `json:"IdentificationDocument"`
	IDDocNumber string `json:"IdentificationDocumentNumber"`
}
