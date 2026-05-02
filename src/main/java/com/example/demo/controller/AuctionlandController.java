package com.example.demo.controller;

import com.example.demo.entity.LocationCode;
import com.example.demo.repository.LocationCodeRepository;
import com.example.demo.service.AuctionlandService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.io.IOException;

import javax.annotation.PostConstruct;

import java.util.List;
import java.util.Optional;


@RestController
@RequestMapping("/api/auctionland")
public class AuctionlandController {

    private final AuctionlandService auctionlandService;
    private final LocationCodeRepository locationCodeRepository;

    public AuctionlandController(AuctionlandService auctionlandService, LocationCodeRepository locationCodeRepository){
        //생성자
        this.auctionlandService = auctionlandService;
        this.locationCodeRepository = locationCodeRepository;
    }

    @PostConstruct
    public void insertLocationCodeInformation(){
        // 법정동 코드 등록하기 위한 방법2.
        // 법정동 코드 등록을 위해 PostConstruct 를 쓰려 했으나, CommandLineRunner 기반의 프로그램 스타트 로직 실행시 구동되는 부분에
        // 구현 해둠. 현 부분 안씀.
        //System.out.println("법정동 정보 등록 완료");
    }

    @GetMapping("/getSidoLocationNameList")
    public ResponseEntity<List<String>> getSidoLocationNameList()
    {
        return auctionlandService.getSidoLocationNameList();
    }

    @GetMapping("/getSiguLocationNameList")
    public ResponseEntity<List<String>> getSiguLocationNameList(@RequestParam String sidoData)
    {
        return auctionlandService.getSiguLocationNameList(sidoData);
    }

    @GetMapping("/getSidongLocationNameList")
    public ResponseEntity<List<String>> getSidongLocationNameList(@RequestParam String sidoData, @RequestParam String siguData)
    {
        return auctionlandService.getSidongLocationNameList(sidoData, siguData);
    }

    @GetMapping("/getSiriLocationNameList")
    public ResponseEntity<List<String>> getSiriLocationNameList(@RequestParam String sidoData, @RequestParam String siguData, @RequestParam String sidongData)
    {
        return auctionlandService.getSiriLocationNameList(sidoData, siguData, sidongData);
    }


    @GetMapping("/getLocationCodeData")
    public ResponseEntity<Optional<LocationCode>> getLocationCodeData(@RequestParam String daepyoSidoCd, @RequestParam String daepyoSiguCd, @RequestParam String daepyoSidongCd, @RequestParam String daepyoSiriCd) throws IOException {

        return auctionlandService.getLocationCodeData(daepyoSidoCd, daepyoSiguCd, daepyoSidongCd, daepyoSiriCd);

    }

//    @GetMapping("/getRealTradeData")
//    public ResponseEntity<Optional<LocationCode>> getRealTradeData(@RequestParam String locationCode) throws IOException {
//
//        return auctionlandService.getLocationCodeData(daepyoSidoCd, daepyoSiguCd, daepyoSidongCd, daepyoSiriCd);
//
//    }


    @GetMapping("/getAuctionData")
    public ResponseEntity<List<String>> getAuctionData(@RequestParam String daepyoSidoCd, @RequestParam String daepyoSiguCd, @RequestParam String daepyoSidongCd, @RequestParam String daepyoSiriCd) throws IOException {

        return auctionlandService.getAuctionData(daepyoSidoCd, daepyoSiguCd, daepyoSidongCd, daepyoSiriCd);

    }

    @GetMapping("/testCall2")
    public String testCall2()
    {
        System.out.println("API Call Test Success");
        return "강하늘 붐돌맘";
        //웹훅 테스트2
    }
}
