#Headers

Request URL: https://gql.waveapps.com/graphql/internal
Request Method: POST
:authority: gql.waveapps.com
:method: POST
:path: /graphql/internal
:scheme: https
accept: */*
accept-encoding: gzip, deflate, br, zstd
accept-language: en-US,en;q=0.9,fr;q=0.8
authorization: Bearer 6KVwOJ00nEBOW1IYW8jCSsHbIMkms3
content-length: 3279
content-type: application/json
msa-token: 
origin: https://next.waveapps.com
priority: u=1, i
referer: https://next.waveapps.com/
sec-ch-ua: "Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"
sec-ch-ua-mobile: ?0
sec-ch-ua-platform: "Windows"
sec-fetch-dest: empty
sec-fetch-mode: cors
sec-fetch-site: same-site
stepup-auth-tokens: 
user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36

#Payload

{"operationName":"TransactionCreate","variables":{"input":{"businessId":"QnVzaW5lc3M6ZTQ1N2YwZjQtMzM4OC00NDM3LWI3YjUtZWU2NTI1ZWE5YWRi","date":"2026-05-18","description":"Test Trans","anchorLineItem":{"category":{"type":"ACCOUNT_ID","accountId":"QWNjb3VudDo1OTg3OTgyMzc1MDMxMTkxMDI7QnVzaW5lc3M6ZTQ1N2YwZjQtMzM4OC00NDM3LWI3YjUtZWU2NTI1ZWE5YWRi"},"amount":"100.00","itemType":"CREDIT"},"lineItems":[{"category":{"type":"ACCOUNT_ID","accountId":"QWNjb3VudDo1OTg3OTgyMzgzMTY4MTQxMTI7QnVzaW5lc3M6ZTQ1N2YwZjQtMzM4OC00NDM3LWI3YjUtZWU2NTI1ZWE5YWRi"},"amount":"100.00","itemType":"DEBIT","taxAction":null}]}},"query":"mutation TransactionCreate($input: TransactionCreateInput!) {\n  transactionCreate(input: $input) {\n    didSucceed\n    inputErrors {\n      code\n      message\n      path\n      __typename\n    }\n    transaction {\n      ...TransactionFragment\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment AccountFragment on Account {\n  id\n  name\n  accrualAnchorTier\n  isArchived\n  isPaymentsByWaveAccount\n  currency {\n    code\n    __typename\n  }\n  subtype {\n    name\n    value\n    type {\n      value\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment SalesTaxFragment on SalesTax {\n  id\n  abbreviation\n  name\n  rate\n  isArchived\n  isRecoverable\n  __typename\n}\n\nfragment TransactionLineItemFragment on ClientTransactionLineItem {\n  account {\n    ...AccountFragment\n    __typename\n  }\n  amount\n  accountAmount\n  businessAmount\n  customer {\n    id\n    name\n    isArchived\n    __typename\n  }\n  vendor {\n    id\n    name\n    isArchived\n    __typename\n  }\n  description\n  itemType\n  label\n  matchedPeriodId\n  matchedPeriod {\n    id\n    endDate\n    status\n    __typename\n  }\n  isReconciled\n  order\n  taxAction\n  taxSummary {\n    totalTaxAmount\n    taxLiabilities {\n      accountId\n      isTaxAmountManuallySet\n      amount\n      salesTax {\n        ...SalesTaxFragment\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  meta {\n    metaEntityType\n    __typename\n  }\n  autocatCategoryStatus\n  tags {\n    id\n    name\n    archived\n    __typename\n  }\n  __typename\n}\n\nfragment TransactionFragment on ClientTransaction {\n  id\n  amount\n  notes\n  date\n  dateCreated\n  description\n  direction\n  sequence\n  userModifiedAt\n  verificationStatus\n  currency {\n    code\n    __typename\n  }\n  origin {\n    externalId\n    description\n    type\n    __typename\n  }\n  anchorLineItem {\n    ...TransactionLineItemFragment\n    __typename\n  }\n  lineItems {\n    ...TransactionLineItemFragment\n    __typename\n  }\n  detailActions {\n    amount\n    date\n    description\n    account\n    category\n    verificationStatus\n    direction\n    notes\n    vendor\n    customer\n    lineItems\n    save\n    split\n    canDelete\n    copy\n    attachment\n    salesTax\n    lineItemAmount\n    __typename\n  }\n  listActions {\n    amount\n    date\n    description\n    account\n    category\n    verificationStatus\n    attachment\n    __typename\n  }\n  mergedFrom {\n    transactionId\n    __typename\n  }\n  mergeSource\n  mergedVerificationState\n  attachment {\n    id\n    type\n    __typename\n  }\n  missingFields\n  active\n  __typename\n}"}