// App — design canvas presenting all five music team views side-by-side.

function App() {
  return (
    <DesignCanvas>
      <DCSection id="overview" title="Overview" subtitle="JBC Music Team · Sunday morning + evening · 9 roles per service">
        <DCArtboard id="lineup"      label="Lineup · Assignment grid"        width={1280} height={1240}><Lineup /></DCArtboard>
        <DCArtboard id="roles"       label="Roles & preferences · Matrix"    width={1280} height={900}><RolesPrefs /></DCArtboard>
      </DCSection>
      <DCSection id="exceptions" title="Exceptions" subtitle="When someone can't serve">
        <DCArtboard id="unavail"     label="Unavailability & declines"       width={1280} height={900}><Unavail /></DCArtboard>
      </DCSection>
      <DCSection id="touchpoints" title="Touchpoints" subtitle="What members and the worship leader actually do">
        <DCArtboard id="member"      label="Member view · Mobile"            width={440} height={900}><MemberView /></DCArtboard>
        <DCArtboard id="notify"      label="Worship leader · Send to team"   width={1280} height={900}><Notify /></DCArtboard>
      </DCSection>
      <DCSection id="onboarding" title="Onboarding" subtitle="How a new music team member joins the system">
        <DCArtboard id="register"   label="Public registration form"        width={900}  height={1280}><Register /></DCArtboard>
        <DCArtboard id="emails"     label="Email templates · Receipt + Verification" width={900} height={1700}><EmailTemplates /></DCArtboard>
      </DCSection>
    </DesignCanvas>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
