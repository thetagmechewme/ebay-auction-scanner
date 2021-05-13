#!/usr/bin/env python3

#TODO - time left low for auction sniping

import datetime
from ebaysdk.exception import ConnectionError
from ebaysdk.finding import Connection
import pygsheets

#Params
#Info (str) - Used for logging
#searchTerms (str) - Determines what auctions to search
#dataIndex (int) - Determines index for data training in Google Sheets
#buyIndex (int) - Determines index for auctions to buy in Google Sheets
#fromCountry (str) - Determines what country to look for auctions in
#condition (str) - Determines what condition of item to look for
#buyNow (str) - Determines what kind of auction to look at (ex. bidding vs buy it now)
#shipping (bool) - Determines if we need to ship an item or not (ex. digital item vs physical)
def scanAuctions(info, searchTerms, dataIndex, buyIndex, fromCountry, condition, buyNow, shipping):
	api = Connection(appid='APP_ID_HERE', config_file=None)
	request = {"keywords": searchTerms, "outputSelector": "SellerInfo"}
	auction = api.execute('findItemsAdvanced', request)
	assert(auction.reply.ack == 'Success')
	assert(type(auction.reply.timestamp) == datetime.datetime)
	assert(type(auction.reply.searchResult.item) == list)
	auctions = auction.reply.searchResult.item
	assert(type(auction.dict()) == dict)
	auth = pygsheets.authorize(service_file='PATH_HERE')
	sheet = auth.open('eBay')
	worksheet = sheet[dataIndex]
	dupeURL = ''
	print("Looping through " + str(len(auctions)) + info)

	for item in auctions:
		itemName =  item.get('title')
		itemCountry = item.get('country')
		itemLocation = item.get('location')
		itemShippingType = item.shippingInfo.get('shippingType')
		itemCost = item.sellingStatus.get('convertedCurrentPrice').value
		itemBuyNow = item.listingInfo.get('listingType')
		itemStatus = item.sellingStatus.get('sellingState')
		itemCondition = item.condition.get('conditionDisplayName')
		itemURL = item.get('viewItemURL')
		itemStart = str(item.listingInfo.get('startTime'))
		itemEnd = str(item.listingInfo.get('endTime'))
		sellerFeedbackscore = int(item.sellerInfo.get('feedbackScore'))
		sellerPositiveFeedback = float(item.sellerInfo.get('positiveFeedbackPercent'))

		listOfURLS = worksheet.find(itemURL)

		if(len(listOfURLS) == 1):
			dupeURL = str(listOfURLS[0])

		if(itemURL not in dupeURL and fromCountry in itemCountry and itemBuyNow == buyNow and itemCondition == condition and sellerFeedbackscore > 0 and sellerPositiveFeedback >= 90):
			cells = worksheet.get_all_values(include_tailing_empty_rows=False, include_tailing_empty=False, returnas='matrix')
			lastRow = len(cells)
			worksheet.insert_rows(lastRow, number=1, values=[itemName, itemCountry, itemLocation, itemShippingType, itemBuyNow, itemStatus, itemURL, itemStart, itemEnd, itemCost])
	
	cell = worksheet.range('L2:L2')

	if(len(cell) == 1):
		avg = str(cell[0])
		replacementChars = "[<CellL2'$>]"
		for char in avg:
			if char in replacementChars:
				avg = avg.replace(char, '').strip()

	for item in auctions:
		itemName =  item.get('title')
		itemCountry = item.get('country')
		itemLocation = item.get('location')
		itemShippingType = item.shippingInfo.get('shippingType')
		itemCost = float(item.sellingStatus.get('convertedCurrentPrice').value)
		itemBuyNow = item.listingInfo.get('listingType')
		itemStatus = item.sellingStatus.get('sellingState')
		itemCondition = item.condition.get('conditionDisplayName')
		itemURL = item.get('viewItemURL')
		itemStart = str(item.listingInfo.get('startTime'))
		itemEnd = str(item.listingInfo.get('endTime'))
		sellerFeedbackscore = int(item.sellerInfo.get('feedbackScore'))		
		sellerPositiveFeedback = float(item.sellerInfo.get('positiveFeedbackPercent'))

		avg = float(avg)
		profit = (avg-itemCost)
		fees = (avg * .25) if shipping else (avg * .15)
		if(profit > fees):
			worksheet = sheet[buyIndex]
			listOfURLS = worksheet.find(itemURL)
			if(len(listOfURLS) == 1):
				dupeURL = str(listOfURLS[0])
			if(itemURL not in dupeURL and fromCountry in itemCountry and itemBuyNow == buyNow and itemCondition == condition and sellerFeedbackscore > 0 and sellerPositiveFeedback >= 90):
					cells = worksheet.get_all_values(include_tailing_empty_rows=False, include_tailing_empty=False, returnas='matrix')		
					lastRow = len(cells)
					worksheet.insert_rows(lastRow, number=1, values=[itemName, itemCountry, itemLocation, itemShippingType, itemBuyNow, itemStatus, itemURL, itemStart, itemEnd, itemCost, profit])

#Xbox Game Pass Ultimate
scanAuctions('Game Pass auctions', 'game pass ultimate trial', 0, 3, 'US', 'New', 'FixedPrice', False)

#Xbox Series X
scanAuctions('XBSX auctions', 'xbox series x', 1, 4, 'US', 'New','FixedPrice', True)

#PS5
scanAuctions('PS5 auctions', 'playstation 5', 2, 5, 'US', 'New', 'FixedPrice', True)

