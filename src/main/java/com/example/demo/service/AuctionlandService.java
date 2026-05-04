package com.example.demo.service;

import com.example.demo.entity.LocationCode;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;

import java.net.http.HttpResponse;
import java.util.HashMap;
import java.util.List;
import java.util.Optional;


public interface AuctionlandService {
    public ResponseEntity<List<String>> getSidoLocationNameList();
    public ResponseEntity<List<String>> getSiguLocationNameList(String sidoData);
    public ResponseEntity<List<String>> getSidongLocationNameList(String sidoData, String siguData);

    public ResponseEntity<List<String>> getSiriLocationNameList(String sidoData, String siguData, String sidongData);
    public ResponseEntity<Optional<LocationCode>> getLocationCodeData(String daepyoSidoCd, String daepyoSiguCd, String daepyoSidongCd, String daepyoSiriCd);


        ResponseEntity<List<String>> getAuctionData(String daepyoSidoCd, String daepyoSiguCd, String daepyoSidongCd, String daepyoSiriCd);

    //List<LocationCode> findLocationCodeByCriteria(String SidoCd, String SiguCd, String SidongCd, String SiriCd);
}
