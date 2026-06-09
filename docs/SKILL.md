# 1C Assistant Skill Guidelines

This document outlines standard guidelines for the AI assistant when working with 1C:Enterprise configurations, code modifications, and database operations.

## 1. Static Configuration Analysis
When analyzing 1C metadata or queries from an unpacked configuration dump (like `1C_tester`):
1. **Find objects**: Search directory structures (`Documents`, `Catalogs`, `AccumulationRegisters`, `InformationRegisters`, `Reports`) for object names.
2. **Extract query texts**: DCS reports store their main dataset query inside `<query>` tags in `Template.xml` (e.g. `Reports\<ReportName>\Templates\ОсновнаяСхемаКомпоновкиДанных\Ext\Template.xml`).
3. **Analyze Postings**: Register postings are described in the document's `.xml` file inside `<RegisterRecords>` tags. The posting logic is written in the document's object module (`ObjectModule.bsl` or `Ext\ObjectModule.bsl`).

## 2. Dynamic Data Operations via OData REST API
1C:Enterprise has a built-in OData REST interface. To query or edit database tables:
1. Ensure OData is enabled in the 1C application:
   * Execute: `НачатьНастройкуСоставаСтандартногоODataИнтерфейса(МассивОбъектов)` in 1C built-in language to expose tables.
2. Endpoint format: `http://<host>/<database>/odata/standard.odata/`
3. Table names mapping:
   * **Catalogs**: `Catalog_<Name>` (e.g. `Catalog_Номенклатура`, `Catalog_Организации`)
   * **Documents**: `Document_<Name>` (e.g. `Document_СписаниеЗапасов`)
   * **Registers (Accumulation)**: `AccumulationRegister_<Name>`
   * **Registers (Information)**: `InformationRegister_<Name>`
4. Operations:
   * **Read**: `GET http://<odata_url>/Catalog_Номенклатура?$filter=Code eq '001'&$select=Ref_Key,Description`
   * **Create**: `POST http://<odata_url>/Catalog_Номенклатура` with JSON payload.
   * **Update**: `PATCH http://<odata_url>/Catalog_Номенклатура(guid'xxxx-xxxx-xxxx')` with JSON payload.

## 3. Best Practices for 1C Queries
To ensure optimal performance and standard compliance when writing 1C queries:
* **Always use `ВЫРАЗИТЬ`**: When referencing fields on composite type fields (such as `Регистратор`, `ДокументПродажи`, `ДокументОснование`), explicitly cast them to concrete types:
  ```sql
  ВЫРАЗИТЬ(ЗапасыОбороты.Регистратор КАК Документ.ОприходованиеЗапасов).ДокументОснование
  ```
  This prevents unnecessary implicit SQL table joins (`LEFT JOIN` across all possible reference types).
* **Query Virtual Tables instead of Physical**: Always read aggregates and balances from virtual tables (e.g., `РегистрНакопления.Запасы.Обороты` or `РегистрНакопления.Запасы.Остатки`) instead of scanning raw physical table entries.
* **Filter inside Virtual Table Parameters**: Never put index-filtering (like date range, organization, warehouse) in the `ГДЕ` (WHERE) clause if querying a virtual table. Always pass them as virtual table parameters:
  ```sql
  // CORRECT
  РегистрНакопления.Запасы.Обороты(&НачалоПериода, &КонецПериода, Авто, Организация = &Организация)
  
  // INCORRECT
  РегистрНакопления.Запасы.Обороты(, , Авто, ) КАК Запасы
  ГДЕ Запасы.Период >= &НачалоПериода И Запасы.Организация = &Организация
  ```
* **Use Temporary Tables (`ПОМЕСТИТЬ`)**: Break down complex queries into multiple steps using temp tables. Avoid nesting subqueries inside the `ИЗ` (FROM) clause, as the SQL query optimizer might compile them inefficiently.
* **Calculate Net Movements via `Приход - Расход`**: For reports supporting adjustments, calculations should use the net change:
  `ЗапасыОбороты.КоличествоПриход - ЗапасыОбороты.КоличествоРасход КАК Количество`
  This automatically supports negative or positive corrections in either direction.
