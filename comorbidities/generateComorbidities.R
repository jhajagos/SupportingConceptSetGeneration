
install.packages("comorbidity")

library(comorbidity)

df <- comorbidity::icd10cm_2022
df["id"] <- 1:nrow(df)

icd10_cm_map_charl <- comorbidity::comorbidity(x=df,code="Code", id="id", map="charlson_icd10_quan", assign0=FALSE)
icd10_cm_map_elix <- comorbidity::comorbidity(x=df,code="Code", id="id", map="elixhauser_icd10_quan", assign0=FALSE)

write.csv(df,"./icd10_cm_map_codes.csv", row.names=FALSE)
write.csv(icd10_cm_map_elix,"./icd10_cm_map_elix.csv")
write.csv(icd10_cm_map_charl, "./icd10_cm_map_charl.csv", row.names = FALSE)