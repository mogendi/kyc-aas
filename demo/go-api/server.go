package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"

	"github.com/gorilla/mux"
	"github.com/mogendi/models"
	"github.com/sirupsen/logrus"
)

const port = ":8000"

// IndexHandler handles requests for the "/identification" resource
func IndexHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	// Create a new struct
	var newIdentificationDoc models.IdentificationDocumentInput

	// Read details of our request
	reqBody, err := ioutil.ReadAll(r.Body)
	if err != nil {
		fmt.Fprintf(w, "Kindly specify the document type and document number")
	}

	// convert the json into a struct
	json.Unmarshal(reqBody, &newIdentificationDoc)

	if newIdentificationDoc.IDDocNumber == "" || newIdentificationDoc.IDDocType == "" {
		fmt.Fprintf(w, "The `id document type` and `document number` should be defined")
		return
	}

	json.NewEncoder(w).Encode(newIdentificationDoc)
}

func main() {
	router := mux.NewRouter()

	router.HandleFunc("/identification", IndexHandler).Methods(http.MethodPost)
	err := http.ListenAndServe(port, router)
	if err != nil {
		logrus.Printf("Error encountered while starting server is: %v", err)
		return
	}
}
