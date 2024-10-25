from virtaccl.site.SNS_Linac.virtual_SNS_linac import build_sns
from virtaccl.site.BTF.btf_virtual_accelerator import build_btf


sns = build_sns()

print(sns.get_value("SCL_Mag:DCH00:B"), sns.get_value("SCL_Mag:DCH01:B"), sns.get_value("SCL_Diag:BPM04:xAvg"))
sns.set_values({"SCL_Mag:PS_DCH00:B_Set": 0.01, "SCL_Mag:PS_DCH01:B_Set": -0.01})
print(sns.get_value("SCL_Mag:DCH00:B"), sns.get_value("SCL_Mag:DCH01:B"), sns.get_value("SCL_Diag:BPM04:xAvg"))


btf = build_btf()

print(btf.get_value("BTF_MEBT_Mag:DCH01:B"), btf.get_value("BTF_MEBT_Mag:DCH02:B"), btf.get_value("ITSF_Diag:BPM04_4:xAvg"))
btf.set_values({"BTF_MEBT_Mag:PS_DCH01:I_Set": 2, "BTF_MEBT_Mag:PS_DCH02:I_Set": 3})
print(btf.get_value("BTF_MEBT_Mag:DCH01:B"), btf.get_value("BTF_MEBT_Mag:DCH02:B"), btf.get_value("ITSF_Diag:BPM04_4:xAvg"))

